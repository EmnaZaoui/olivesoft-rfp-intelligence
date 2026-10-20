from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models import Tender, Prospect, ProposalDraft, RequirementMatch, CompetitorInsight
from app.agents.proposal_crew import generate_proposal_with_crew


def generate_full_proposal(db: Session, tender_id: str) -> ProposalDraft:
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender introuvable")
    if tender.status not in ("researched", "drafted"):
        raise HTTPException(status_code=400, detail="Le prospect doit d'abord être recherché (/research)")

    prospect = (
        db.query(Prospect).filter(Prospect.tender_id == tender.id)
        .order_by(Prospect.created_at.desc()).first()
    )
    if not prospect:
        raise HTTPException(status_code=400, detail="Aucune recherche prospect trouvée")

    matrix = db.query(RequirementMatch).filter(RequirementMatch.tender_id == tender.id).all()
    competitor = (
        db.query(CompetitorInsight).filter(CompetitorInsight.tender_id == tender.id)
        .order_by(CompetitorInsight.created_at.desc()).first()
    )

    tender_dict = {
        "title": tender.title, "issuing_organization": tender.issuing_organization,
        "sector": tender.sector, "estimated_budget": tender.estimated_budget, "summary": tender.summary,
    }
    prospect_dict = {
        "company_name": prospect.company_name, "sector": prospect.sector,
        "estimated_revenue": prospect.estimated_revenue,
        "key_partners": prospect.key_partners, "past_projects": prospect.past_projects,
    }
    matrix_list = [
        {
            "requirement_text": m.requirement_text, "covered": m.covered, "score": m.score,
            "best_document_title": m.best_document_title, "concrete_evidence": m.concrete_evidence,
            "justification": m.justification,
        } for m in matrix
    ]
    competitor_dict = None
    if competitor:
        competitor_dict = {
            "estimated_budget_range": competitor.estimated_budget_range,
            "confidence": competitor.confidence,
            "competitive_positioning": competitor.competitive_positioning,
            "likely_competitors": competitor.likely_competitors,
        }

    result = generate_proposal_with_crew(tender_dict, prospect_dict, matrix_list, competitor_dict)

    draft = ProposalDraft(
        tender_id=tender.id,
        content_markdown=result["content_markdown"],
        content_sections=result["content_sections"],
        status="approved" if result["approved"] else "needs_review",
        review_feedback=result["review_feedback"],
        iterations=result["iterations"],
    )
    db.add(draft)
    tender.status = "drafted"
    db.commit()
    db.refresh(draft)
    return draft