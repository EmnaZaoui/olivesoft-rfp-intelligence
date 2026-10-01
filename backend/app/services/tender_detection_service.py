from sqlalchemy.orm import Session

from app.models import Tender
from app.services.serper_client import search_web
from app.services.scraper_service import scrape_page_text
from app.services.extraction_service import extract_tender_fields
from app.services.content_quality import is_content_sufficient, looks_like_listing_page
from app.services.portal_sources import discover_tender_links, discover_links_from_known_portals

_seen_urls_this_run = set()

DEFAULT_SEARCH_QUERIES = [
    "\"appel d'offres\" développement logiciel Tunisie cahier des charges 2026",
    "\"appel d'offres\" plateforme web Tunisie date limite",
    "RFP software development services deadline 2026",
    "tender IT digital transformation services budget deadline",
]

MAX_LISTING_EXPANSION = 5


def _create_tender_if_valid(db: Session, url: str, raw_text: str, fallback_snippet: str = "") -> Tender | None:
    if db.query(Tender).filter(Tender.source_url == url).first():
        return None  # déjà connu, on évite les doublons

    if not is_content_sufficient(raw_text):
        if fallback_snippet and len(fallback_snippet) > 80:
            raw_text = fallback_snippet
        else:
            return None  # edge case: rien d'exploitable, on ignore proprement sans casser le pipeline

    tender = Tender(source="dynamic_search", source_url=url, raw_text=raw_text, status="new")
    db.add(tender)
    return tender


def _process_url(db: Session, url: str, fallback_snippet: str = "", depth: int = 0) -> list[Tender]:
    if url in _seen_urls_this_run:
        return []
    _seen_urls_this_run.add(url)

    if db.query(Tender).filter(Tender.source_url == url).first():
        return []

    created = []
    scraped = scrape_page_text(url)

    if scraped.startswith("SCRAPE_ERROR"):
        tender = _create_tender_if_valid(db, url, scraped, fallback_snippet)
        if tender:
            created.append(tender)
        return created

    if looks_like_listing_page(scraped) and depth == 0:
        sub_links = discover_tender_links(url)[:MAX_LISTING_EXPANSION]
        for sub_url in sub_links:
            if sub_url in _seen_urls_this_run:
                continue
            created.extend(_process_url(db, sub_url, depth=depth + 1))
        return created

    tender = _create_tender_if_valid(db, url, scraped, fallback_snippet)
    if tender:
        created.append(tender)
    return created


def ingest_dynamic_tenders(db: Session, queries: list[str] | None = None, results_per_query: int = 4) -> list[Tender]:
    queries = queries or DEFAULT_SEARCH_QUERIES
    all_created = []

    for query in queries:
        for result in search_web(query, num_results=results_per_query):
            url = result.get("link", "")
            if not url:
                continue
            all_created.extend(_process_url(db, url, fallback_snippet=result.get("snippet", "")))

    db.commit()
    for t in all_created:
        db.refresh(t)
    return all_created


def ingest_from_portals(db: Session) -> list[Tender]:
    """Crawler dédié sur des portails connus (bonus Multi-Source Crawler)."""
    created = []
    for url in discover_links_from_known_portals():
        created.extend(_process_url(db, url))

    db.commit()
    for t in created:
        db.refresh(t)
    return created


def ingest_manual_tender(db: Session, source: str, raw_text: str) -> Tender:
    tender = Tender(source=source, raw_text=raw_text, status="new")
    db.add(tender)
    db.commit()
    db.refresh(tender)
    return tender


def run_extraction(db: Session, tender: Tender) -> Tender:
    if not is_content_sufficient(tender.raw_text, min_length=150):
        tender.status = "extraction_failed"
        db.commit()
        return tender

    fields = extract_tender_fields(tender.raw_text)
    tender.title = fields["title"]
    tender.issuing_organization = fields.get("issuing_organization", "unknown")
    tender.sector = fields["sector"]
    tender.estimated_budget = fields["estimated_budget"]
    tender.deadline = fields["deadline"]
    tender.requirements = fields["requirements"]
    tender.summary = fields["summary"]
    tender.status = "extracted"

    db.commit()
    db.refresh(tender)
    return tender