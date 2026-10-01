from mcp.server.fastmcp import FastMCP

from app.database import SessionLocal
from app.services.serper_client import search_web
from app.services.scraper_service import scrape_page_text
from app.services.rag_service import search_similar_chunks
from app.models import Tender, ProposalDraft

mcp = FastMCP("olivesoft-tools", host="127.0.0.1", port=8100)


@mcp.tool()
def web_search(query: str) -> str:
    """Recherche web via Serper API, retourne un résumé textuel des résultats."""
    results = search_web(query, num_results=5)
    if not results:
        return "Aucun résultat trouvé pour cette recherche."
    if results[0].get("title") == "ERROR":
        return results[0]["snippet"]

    return "\n".join(f"- {r['title']}: {r['snippet']} (source: {r['link']})" for r in results)


@mcp.tool()
def scrape_url(url: str) -> str:
    """Récupère et nettoie le contenu textuel d'une page web donnée."""
    return scrape_page_text(url)


@mcp.tool()
def search_internal_knowledge(query: str, top_k: int = 5) -> str:
    """Recherche dans la base de connaissances interne OliveSoft (CV, projets) via RAG."""
    db = SessionLocal()
    try:
        results = search_similar_chunks(db, query, top_k)
    finally:
        db.close()

    if not results:
        return "Aucune référence interne trouvée pour cette requête."
    return "\n".join(
        f"- [{r['doc_type']}] {r['document_title']} (score {r['score']}): {r['content'][:300]}"
        for r in results
    )


@mcp.tool()
def get_tender_data(tender_id: str) -> str:
    """Récupère les informations structurées d'un tender depuis la base de données."""
    db = SessionLocal()
    try:
        tender = db.query(Tender).filter(Tender.id == tender_id).first()
    finally:
        db.close()

    if not tender:
        return f"Aucun tender trouvé avec l'id {tender_id}."
    return (
        f"Titre: {tender.title}\nSecteur: {tender.sector}\n"
        f"Budget: {tender.estimated_budget}\nExigences: {tender.requirements}\n"
        f"Résumé: {tender.summary}"
    )


@mcp.tool()
def save_proposal_draft(tender_id: str, content: str) -> str:
    """Sauvegarde un brouillon de proposition pour un tender donné."""
    db = SessionLocal()
    try:
        draft = ProposalDraft(tender_id=tender_id, content_markdown=content)
        db.add(draft)
        db.commit()
        draft_id = draft.id
    except Exception as e:
        db.rollback()
        return f"Erreur lors de la sauvegarde: {e}"
    finally:
        db.close()
    return f"Draft sauvegardé avec succès (id: {draft_id})."


if __name__ == "__main__":
    mcp.run(transport="sse")