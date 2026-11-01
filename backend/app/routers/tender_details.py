from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Prospect, CompetitorInsight, ProposalDraft, User
from app.schemas import ProspectOut, CompetitorInsightOut, ProposalDraftOut
from app.security import get_current_user
from app.agents.proposal_crew import SECTION_TITLES

router = APIRouter(prefix="/tenders", tags=["tender details"])
proposal_router = APIRouter(prefix="/proposals", tags=["proposals"])


@router.get("/{tender_id}/prospect", response_model=Optional[ProspectOut])
def latest_prospect(tender_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return (
        db.query(Prospect).filter(Prospect.tender_id == tender_id)
        .order_by(Prospect.created_at.desc()).first()
    )


@router.get("/{tender_id}/insights", response_model=Optional[CompetitorInsightOut])
def latest_insights(tender_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return (
        db.query(CompetitorInsight).filter(CompetitorInsight.tender_id == tender_id)
        .order_by(CompetitorInsight.created_at.desc()).first()
    )


@router.get("/{tender_id}/proposal", response_model=Optional[ProposalDraftOut])
def latest_proposal(tender_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return (
        db.query(ProposalDraft).filter(ProposalDraft.tender_id == tender_id)
        .order_by(ProposalDraft.created_at.desc()).first()
    )


class SectionSaveIn(BaseModel):
    content: str


@proposal_router.post("/{draft_id}/sections/{section_key}/save", response_model=ProposalDraftOut)
def save_section(draft_id: str, section_key: str, payload: SectionSaveIn,
                 db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Édition manuelle d'une section par le commercial (human in the loop, sans IA)."""
    draft = db.query(ProposalDraft).filter(ProposalDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Proposition introuvable")
    if section_key not in SECTION_TITLES:
        raise HTTPException(status_code=400, detail="Section inconnue")

    text = payload.content.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Le contenu ne peut pas être vide")
    if not text.lstrip().startswith("#"):
        text = f"## {SECTION_TITLES[section_key]}\n\n{text}"

    sections = dict(draft.content_sections or {})
    sections[section_key] = text
    draft.content_sections = sections
    draft.content_markdown = "\n\n".join(sections[k] for k in SECTION_TITLES if k in sections)
    db.commit()
    db.refresh(draft)
    return draft