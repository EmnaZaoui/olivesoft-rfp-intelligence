from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Tender, ProposalDraft, RequirementMatch, CompetitorInsight
from app.services.deck_generator import generate_pptx
from app.services.pdf_export import convert_pptx_to_pdf
from app.agents.proposal_crew import SECTION_TITLES

router = APIRouter(prefix="/exports", tags=["exports"])


def _prepare_deck_inputs(db: Session, draft_id: str):
    draft = db.query(ProposalDraft).filter(ProposalDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Proposition introuvable")
    tender = db.query(Tender).filter(Tender.id == draft.tender_id).first()
    matrix = (
        db.query(RequirementMatch).filter(RequirementMatch.tender_id == tender.id)
        .order_by(RequirementMatch.score.desc()).all()
    )
    competitor = (
        db.query(CompetitorInsight).filter(CompetitorInsight.tender_id == tender.id)
        .order_by(CompetitorInsight.created_at.desc()).first()
    )

    budget_display = tender.estimated_budget
    if (not budget_display or budget_display.lower() == "unknown") and competitor \
            and competitor.estimated_budget_range and competitor.estimated_budget_range.lower() != "unknown":
        budget_display = f"{competitor.estimated_budget_range} (estimation)"

    tender_dict = {
        "title": tender.title,
        "issuing_organization": tender.issuing_organization,
        "sector": tender.sector,
        "estimated_budget": tender.estimated_budget,
        "budget_display": budget_display,
        "deadline": tender.deadline,
        "summary": tender.summary,
        "qualification_score": tender.qualification_score,
        "technical_fit_score": tender.technical_fit_score,
        "urgent_deadline_alert": tender.urgent_deadline_alert,
    }
    matrix_list = [
        {
            "requirement_text": m.requirement_text, "covered": m.covered, "score": m.score,
            "best_document_title": m.best_document_title, "concrete_evidence": m.concrete_evidence,
        }
        for m in matrix
    ]

    raw_sections = draft.content_sections or {"proposition": draft.content_markdown}
    ordered = {k: raw_sections[k] for k in SECTION_TITLES if k in raw_sections}
    for k, v in raw_sections.items():
        ordered.setdefault(k, v)
    return tender_dict, ordered, matrix_list


@router.post("/proposals/{draft_id}/pptx")
def export_pptx(draft_id: str, db: Session = Depends(get_db)):
    tender_dict, sections, matrix_list = _prepare_deck_inputs(db, draft_id)
    pptx_path = generate_pptx(tender_dict, sections, matrix_list, filename=f"proposal_{draft_id}")
    return FileResponse(
        path=pptx_path, filename=pptx_path.name,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )


@router.post("/proposals/{draft_id}/pdf")
def export_pdf(draft_id: str, db: Session = Depends(get_db)):
    tender_dict, sections, matrix_list = _prepare_deck_inputs(db, draft_id)
    pptx_path = generate_pptx(tender_dict, sections, matrix_list, filename=f"proposal_{draft_id}")
    pdf_path = convert_pptx_to_pdf(pptx_path)
    return FileResponse(path=pdf_path, filename=pdf_path.name, media_type="application/pdf")