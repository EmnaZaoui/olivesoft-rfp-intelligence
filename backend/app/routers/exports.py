from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Tender, ProposalDraft, RequirementMatch
from app.services.deck_generator import generate_pptx
from app.services.pdf_export import convert_pptx_to_pdf

router = APIRouter(prefix="/exports", tags=["exports"])


def _prepare_deck_inputs(db: Session, draft_id: str):
    draft = db.query(ProposalDraft).filter(ProposalDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Proposition introuvable")
    tender = db.query(Tender).filter(Tender.id == draft.tender_id).first()
    matrix = db.query(RequirementMatch).filter(RequirementMatch.tender_id == tender.id).all()

    matrix_list = [
        {"requirement_text": m.requirement_text, "covered": m.covered, "score": m.score}
        for m in matrix
    ]
    tender_dict = {"title": tender.title}
    sections = draft.content_sections or {"proposition": draft.content_markdown}
    return tender_dict, sections, matrix_list


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