from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Tender, Prospect, ProposalDraft
from app.schemas import TenderCreate, TenderOut, ProspectOut

from app.services.tender_detection_service import (
    ingest_dynamic_tenders,
    ingest_from_portals,
    ingest_manual_tender,
    run_extraction,
)

from app.agents.market_intelligence_agent import run_market_intelligence_agent
from app.services.rag_service import search_similar_chunks
from app.services.draft_service import generate_initial_draft

router = APIRouter(prefix="/tenders", tags=["tenders"])


@router.post("/ingest/dynamic", response_model=list[TenderOut])
def ingest_dynamic(db: Session = Depends(get_db)):
    return ingest_dynamic_tenders(db)

@router.post("/ingest/portals", response_model=list[TenderOut])
def ingest_portals(db: Session = Depends(get_db)):
    """Crawler dédié sur des portails d'appels d'offres connus (bonus Multi-Source Crawler)."""
    return ingest_from_portals(db)

@router.post("/ingest/manual", response_model=TenderOut)
def ingest_manual(payload: TenderCreate, db: Session = Depends(get_db)):
    return ingest_manual_tender(db, payload.source, payload.raw_text)


@router.get("/", response_model=list[TenderOut])
def list_tenders(db: Session = Depends(get_db)):
    return db.query(Tender).order_by(Tender.created_at.desc()).all()


@router.get("/{tender_id}", response_model=TenderOut)
def get_tender(tender_id: str, db: Session = Depends(get_db)):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender introuvable")
    return tender


@router.post("/{tender_id}/extract", response_model=TenderOut)
def extract_tender(tender_id: str, db: Session = Depends(get_db)):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender introuvable")
    return run_extraction(db, tender)


@router.post("/{tender_id}/research", response_model=ProspectOut)
def research_prospect(tender_id: str, db: Session = Depends(get_db)):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender introuvable")
    if tender.status not in ("extracted", "researched", "drafted"):
        raise HTTPException(status_code=400, detail="Le tender doit d'abord être extrait (/extract)")

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
        company_name=profile.get("company_name"),
        sector=profile.get("sector"),
        estimated_revenue=profile.get("estimated_revenue"),
        key_partners=profile.get("key_partners"),
        past_projects=profile.get("past_projects"),
        research_notes=profile.get("research_notes"),
        raw_agent_trace={"trace": result["trace"]},
    )
    db.add(prospect)
    tender.status = "researched"
    db.commit()
    db.refresh(prospect)
    return prospect

@router.post("/{tender_id}/draft")
def create_draft(tender_id: str, db: Session = Depends(get_db)):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender introuvable")

    prospect = (
        db.query(Prospect)
        .filter(Prospect.tender_id == tender.id)
        .order_by(Prospect.created_at.desc())
        .first()
    )
    if not prospect:
        raise HTTPException(status_code=400, detail="Aucune recherche prospect trouvée, appelez /research d'abord")

    query = " ".join(tender.requirements or [tender.summary or ""])
    matched_references = search_similar_chunks(db, query=query, top_k=5) if query.strip() else []

    tender_dict = {
        "title": tender.title, "sector": tender.sector,
        "estimated_budget": tender.estimated_budget,
        "requirements": tender.requirements, "summary": tender.summary,
    }
    prospect_dict = {
        "company_name": prospect.company_name, "sector": prospect.sector,
        "estimated_revenue": prospect.estimated_revenue,
        "key_partners": prospect.key_partners, "past_projects": prospect.past_projects,
    }

    draft_content = generate_initial_draft(tender_dict, prospect_dict, matched_references)

    draft = ProposalDraft(tender_id=tender.id, content_markdown=draft_content)
    db.add(draft)
    tender.status = "drafted"
    db.commit()
    db.refresh(draft)

    return {"tender_id": tender.id, "draft_id": draft.id, "content_markdown": draft.content_markdown}