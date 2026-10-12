from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models import Document, DocumentChunk, RequirementMatch, Tender
from app.services.ollama_client import embed_text, chat_json
from app.business_rules import COVERAGE_THRESHOLD

MATCH_SYSTEM_PROMPT = """Tu es un expert technique qui évalue si OliveSoft peut répondre à une
exigence précise d'un appel d'offres, à partir d'extraits de documents internes (CV, projets passés)
et de leurs métadonnées structurées.

Retourne UNIQUEMENT un JSON:
{
  "covered": true ou false,
  "score": 0-100,
  "justification": "pourquoi, en une phrase factuelle",
  "concrete_evidence": "chiffre ou fait concret tiré des métadonnées ou du texte (durée, taille
    d'équipe, budget, nom de client/projet) si disponible, sinon chaîne vide"
}

Sois rigoureux: un extrait vaguement lié ne justifie pas un score élevé. N'invente jamais un chiffre
qui n'est pas explicitement présent dans les candidats fournis.
"""


def _retrieve_candidates(db: Session, requirement: str, top_k: int = 3):
    query_embedding = embed_text(requirement)
    stmt = (
        select(
            DocumentChunk.content,
            Document.title,
            Document.doc_type,
            Document.structured_metadata,
            DocumentChunk.embedding.cosine_distance(query_embedding).label("distance"),
        )
        .join(Document, Document.id == DocumentChunk.document_id)
        .order_by("distance")
        .limit(top_k)
    )
    rows = db.execute(stmt).all()
    return [
        {
            "content": content, "title": title, "doc_type": doc_type,
            "metadata": metadata, "similarity": round(float(1 - distance), 4),
        }
        for content, title, doc_type, metadata, distance in rows
    ]


def score_requirement(db: Session, requirement: str) -> dict:
    candidates = _retrieve_candidates(db, requirement)

    if not candidates:
        return {
            "requirement_text": requirement, "score": 0.0, "covered": False,
            "best_document_title": None,
            "justification": "Aucune référence interne trouvée pour cette exigence.",
            "concrete_evidence": "",
        }

    candidates_text = "\n\n".join(
        f"[Document: {c['title']} ({c['doc_type']})]\nMétadonnées: {c['metadata']}\nExtrait: {c['content'][:500]}"
        for c in candidates
    )
    user_prompt = f"Exigence du tender: {requirement}\n\nCandidats internes disponibles:\n{candidates_text}"

    try:
        judgment = chat_json(MATCH_SYSTEM_PROMPT, user_prompt)
        score = float(judgment.get("score", 0))
        return {
            "requirement_text": requirement,
            "score": score,
            "covered": bool(judgment.get("covered", False)) and score >= COVERAGE_THRESHOLD,
            "best_document_title": candidates[0]["title"],
            "justification": judgment.get("justification", ""),
            "concrete_evidence": judgment.get("concrete_evidence", ""),
        }
    except ValueError:
        # edge case: LLM indisponible ou JSON invalide -> secours par similarité vectorielle pure
        best = max(candidates, key=lambda c: c["similarity"])
        return {
            "requirement_text": requirement,
            "score": round(best["similarity"] * 100, 1),
            "covered": best["similarity"] * 100 >= COVERAGE_THRESHOLD,
            "best_document_title": best["title"],
            "justification": "Évaluation de secours basée sur la similarité vectorielle (LLM indisponible).",
            "concrete_evidence": "",
        }


def run_matching_and_scoring(db: Session, tender: Tender) -> list[RequirementMatch]:
    requirements = tender.requirements or []

    # on repart d'une matrice propre à chaque nouvelle qualification
    db.query(RequirementMatch).filter(RequirementMatch.tender_id == tender.id).delete()

    matches = []
    for requirement in requirements:
        if not requirement or not requirement.strip():
            continue  # edge case: exigence vide dans la liste extraite
        result = score_requirement(db, requirement)
        match = RequirementMatch(tender_id=tender.id, **result)
        db.add(match)
        matches.append(match)

    db.commit()
    for m in matches:
        db.refresh(m)
    return matches