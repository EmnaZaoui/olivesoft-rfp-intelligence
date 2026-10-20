from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Tender, Prospect, RequirementMatch, CompetitorInsight
from app.schemas import TenderCreate, TenderOut, ProspectOut, RequirementMatchOut, CompetitorInsightOut
from app.services.tender_detection_service import (
    ingest_dynamic_tenders, ingest_from_portals, ingest_manual_tender, run_extraction,
    get_last_ingestion_stats,
)
from app.services.matching_service import run_matching_and_scoring
from app.services.qualification_service import qualify_tender
from app.agents.market_intelligence_agent import run_market_intelligence_agent
from app.agents.competitor_budget_agent import run_competitor_budget_agent

from app.services.apify_tender_service import ingest_with_apify, get_last_apify_stats
from app.services.apify_client_service import ApifyUnavailable
from app.services.opendata_sources import ingest_opendata, get_last_opendata_stats

router = APIRouter(prefix="/tenders", tags=["tenders"])


@router.post("/ingest/dynamic", response_model=list[TenderOut])
def ingest_dynamic(max_tenders: int = 15, time_filter: str = "qdr:m", db: Session = Depends(get_db)):
    """Serper (requêtes ciblées) + portails + PDF, filtrés IT/non expirés. time_filter: qdr:w | qdr:m | qdr:y"""
    return ingest_dynamic_tenders(db, max_tenders=max_tenders, time_filter=time_filter)


@router.post("/ingest/portals", response_model=list[TenderOut])
def ingest_portals(max_tenders: int = 15, db: Session = Depends(get_db)):
    return ingest_from_portals(db, max_tenders=max_tenders)


@router.get("/ingest/stats")
def ingest_stats():
    """Explique pourquoi les candidats ont été acceptés ou rejetés lors de la dernière ingestion."""
    return get_last_ingestion_stats()

@router.post("/ingest/apify", response_model=list[TenderOut])
def ingest_apify(max_tenders: int = 10, pre_extract: bool = True, source: str = "google",
                 db: Session = Depends(get_db)):
    """Option Apify. source: google | custom | both. L'ancienne détection (/ingest/dynamic) reste disponible."""
    if source not in ("google", "custom", "both"):
        raise HTTPException(status_code=400, detail="source doit être google, custom ou both")
    try:
        return ingest_with_apify(db, max_tenders=max_tenders, pre_extract=pre_extract, source=source)
    except ApifyUnavailable as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/ingest/apify/stats")
def ingest_apify_stats():
    """Explique, pour la dernière ingestion Apify, pourquoi chaque candidat a été accepté ou rejeté."""
    return get_last_apify_stats()

@router.post("/ingest/manual", response_model=TenderOut)
def ingest_manual(payload: TenderCreate, db: Session = Depends(get_db)):
    return ingest_manual_tender(db, payload.source, payload.raw_text)

@router.post("/ingest/opendata", response_model=list[TenderOut])
def ingest_open_data(max_tenders: int = 10, country: str = "", db: Session = Depends(get_db)):
    """Avis réels via API publique gratuite (Banque mondiale). country: ex 'Tunisia', 'Morocco' (vide = tous)."""
    return ingest_opendata(db, max_tenders=max_tenders, country=country)


@router.get("/ingest/opendata/stats")
def ingest_opendata_stats():
    return get_last_opendata_stats()

@router.get("/", response_model=list[TenderOut])
def list_tenders(db: Session = Depends(get_db)):
    return db.query(Tender).order_by(Tender.created_at.desc()).all()


@router.get("/qualified/list", response_model=list[TenderOut])
def list_qualified(db: Session = Depends(get_db)):
    """Retourne uniquement les tenders ayant passé le seuil de qualification."""
    return (
        db.query(Tender).filter(Tender.status == "qualified")
        .order_by(Tender.qualification_score.desc()).all()
    )


@router.get("/{tender_id}", response_model=TenderOut)
def get_tender(tender_id: str, db: Session = Depends(get_db)):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender introuvable")
    return tender


@router.post("/{tender_id}/extract", response_model=TenderOut)
def extract_tender(tender_id: str, force: bool = False, db: Session = Depends(get_db)):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender introuvable")
    if tender.status != "new" and tender.requirements and not force:
        return tender
    return run_extraction(db, tender)


@router.post("/{tender_id}/qualify", response_model=TenderOut)
def qualify(tender_id: str, db: Session = Depends(get_db)):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender introuvable")
    if tender.status == "rejected_irrelevant":
        return tender  
    if tender.status not in ("extracted", "qualified", "rejected_low_score", "rejected_expired"):
        raise HTTPException(status_code=400, detail="Le tender doit d'abord être extrait (/extract)")

    run_matching_and_scoring(db, tender)
    return qualify_tender(db, tender)

@router.get("/{tender_id}/matrix", response_model=list[RequirementMatchOut])
def get_matrix(tender_id: str, db: Session = Depends(get_db)):
    return db.query(RequirementMatch).filter(RequirementMatch.tender_id == tender_id).all()


@router.post("/{tender_id}/research", response_model=ProspectOut)
def research_prospect(tender_id: str, db: Session = Depends(get_db)):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender introuvable")
    if tender.status not in ("qualified", "researched", "drafted"):
        raise HTTPException(
            status_code=400,
            detail="Le tender doit d'abord être qualifié (/qualify) avec un score suffisant.",
        )

    organization_hint = tender.issuing_organization
    if not organization_hint or organization_hint == "unknown":
        organization_hint = tender.title if tender.title and tender.title != "unknown" else "unknown"

    result = run_market_intelligence_agent(
        organization_hint=organization_hint,
        tender_summary=tender.summary or tender.raw_text[:500],
        tender_sector=tender.sector or "unknown",
    )
    profile = result["profile"]

    prospect = Prospect(
        tender_id=tender.id,
        company_name=profile.get("company_name"), sector=profile.get("sector"),
        estimated_revenue=profile.get("estimated_revenue"),
        key_partners=profile.get("key_partners"), past_projects=profile.get("past_projects"),
        research_notes=profile.get("research_notes"),
        raw_agent_trace={"trace": result["trace"]},
    )
    db.add(prospect)
    tender.status = "researched"
    db.commit()
    db.refresh(prospect)
    return prospect


@router.post("/{tender_id}/competitor-insights", response_model=CompetitorInsightOut)
def competitor_insights(tender_id: str, db: Session = Depends(get_db)):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender introuvable")
    if tender.status not in ("qualified", "researched", "drafted"):
        raise HTTPException(status_code=400, detail="Le tender doit d'abord être qualifié (/qualify)")

    result = run_competitor_budget_agent(
        title=tender.title or "unknown", sector=tender.sector or "unknown",
        estimated_budget=tender.estimated_budget or "unknown", summary=tender.summary or "",
    )
    output = result["output"]

    insight = CompetitorInsight(
        tender_id=tender.id,
        estimated_budget_range=output.get("estimated_budget_range"),
        confidence=output.get("confidence"),
        competitive_positioning=output.get("competitive_positioning"),
        likely_competitors=output.get("likely_competitors"),
        notes=output.get("notes"),
        raw_trace={"trace": result["trace"]},
    )
    db.add(insight)
    db.commit()
    db.refresh(insight)
    return insight