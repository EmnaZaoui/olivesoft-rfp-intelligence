from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Tender, Prospect, ProposalDraft, RequirementMatch
from app.schemas import ProposalDraftOut, SectionEditRequest
from app.services.proposal_generation_service import generate_full_proposal
from app.agents.proposal_crew import regenerate_section_with_prompt, SECTION_TITLES

router = APIRouter(prefix="/proposals", tags=["proposals"])


@router.post("/tenders/{tender_id}/generate", response_model=ProposalDraftOut)
def generate_proposal(tender_id: str, db: Session = Depends(get_db)):
    return generate_full_proposal(db, tender_id)


@router.get("/{draft_id}", response_model=ProposalDraftOut)
def get_proposal(draft_id: str, db: Session = Depends(get_db)):
    draft = db.query(ProposalDraft).filter(ProposalDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Proposition introuvable")
    return draft


@router.post("/{draft_id}/sections/{section_key}/edit", response_model=ProposalDraftOut)
def edit_section(draft_id: str, section_key: str, payload: SectionEditRequest, db: Session = Depends(get_db)):
    """Human-in-the-loop: le commercial donne une instruction libre pour réécrire UNE section."""
    draft = db.query(ProposalDraft).filter(ProposalDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Proposition introuvable")
    if section_key not in SECTION_TITLES:
        raise HTTPException(status_code=400, detail=f"Section inconnue. Valides: {list(SECTION_TITLES.keys())}")

    tender = db.query(Tender).filter(Tender.id == draft.tender_id).first()
    prospect = (
        db.query(Prospect).filter(Prospect.tender_id == tender.id)
        .order_by(Prospect.created_at.desc()).first()
    )
    matrix = db.query(RequirementMatch).filter(RequirementMatch.tender_id == tender.id).all()

    sections = draft.content_sections or {}
    current_content = sections.get(section_key, "")

    tender_dict = {
        "title": tender.title, "issuing_organization": tender.issuing_organization,
        "sector": tender.sector, "estimated_budget": tender.estimated_budget, "summary": tender.summary,
    }
    prospect_dict = {
        "company_name": prospect.company_name if prospect else "à confirmer",
        "sector": prospect.sector if prospect else "à confirmer",
        "estimated_revenue": prospect.estimated_revenue if prospect else "à confirmer",
        "key_partners": prospect.key_partners if prospect else [],
        "past_projects": prospect.past_projects if prospect else [],
    }
    matrix_list = [
        {
            "requirement_text": m.requirement_text, "covered": m.covered, "score": m.score,
            "best_document_title": m.best_document_title, "concrete_evidence": m.concrete_evidence,
            "justification": m.justification,
        } for m in matrix
    ]

    updated_section = regenerate_section_with_prompt(
        section_key, current_content, payload.instruction, tender_dict, prospect_dict, matrix_list
    )

    sections[section_key] = updated_section
    draft.content_sections = sections
    draft.content_markdown = "\n\n".join(sections[k] for k in SECTION_TITLES if k in sections)
    db.commit()
    db.refresh(draft)
    return draft