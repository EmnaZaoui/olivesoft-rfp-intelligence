import logging
from collections import Counter
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

from sqlalchemy.orm import Session

from app.models import Tender
from app.services.serper_client import search_web
from app.services.scraper_service import scrape_many
from app.services.extraction_service import extract_tender_fields
from app.services.search_queries import build_queries
from app.services.portal_sources import discover_tender_links, discover_links_from_known_portals
from app.services.content_quality import (
    is_content_sufficient, looks_like_listing_page, assess_tender_candidate,
    it_relevance_score, negative_score, content_has_tender_signal,
)

logger = logging.getLogger(__name__)

MAX_CANDIDATES_TO_SCRAPE = 40
MAX_LISTING_SUBLINKS = 30
SCRAPE_WORKERS = 4
PREFERRED_DOMAINS = ("j360.info", "appeloffres.com", "tuneps.tn")

_last_stats: dict = {}


def get_last_ingestion_stats() -> dict:
    return _last_stats


def _normalize_url(url: str) -> str:
    p = urlparse(url.strip())
    query = [(k, v) for k, v in parse_qsl(p.query) if not k.lower().startswith("utm_")]
    return urlunparse((p.scheme, p.netloc.lower(), p.path.rstrip("/") or "/", "", urlencode(query), ""))


def _is_known(db: Session, url: str) -> bool:
    return db.query(Tender.id).filter(Tender.source_url.in_([url, _normalize_url(url)])).first() is not None


def _collect_candidates(db: Session, queries: list[str], per_query: int, time_filter: str | None,
                        seen: set[str], stats: Counter) -> list[dict]:
    candidates = []
    for query in queries:
        results = search_web(query, num_results=per_query, time_filter=time_filter, filter_noise=True)
        stats["serper_queries"] += 1
        for r in results:
            url = r.get("link", "")
            if not url:
                if r.get("title") == "ERROR":
                    stats["serper_errors"] += 1
                continue
            norm = _normalize_url(url)
            if norm in seen:
                continue
            seen.add(norm)
            if _is_known(db, url):
                stats["already_known"] += 1
                continue
            candidates.append({"url": url, "title": r.get("title", ""), "snippet": r.get("snippet", "")})
    return candidates


def _prerank(candidates: list[dict]) -> list[dict]:
    """Classement bon marché (titre + snippet) pour ne scraper que les URLs prometteuses."""
    scored = []
    for c in candidates:
        blob = f"{c['title']} {c['snippet']}"
        score = it_relevance_score(blob) * 2
        score += 3 if content_has_tender_signal(blob) else 0
        score -= negative_score(blob) * 3
        if any(d in c["url"] for d in PREFERRED_DOMAINS):
            score += 3
        if c["url"].lower().split("?")[0].endswith(".pdf"):
            score += 1  # les cahiers des charges PDF sont riches en exigences
        scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for score, c in scored if score > -3][:MAX_CANDIDATES_TO_SCRAPE]


def _ingest_urls(db: Session, urls: list[str], max_tenders: int, stats: Counter) -> list[Tender]:
    stats["urls_scraped"] += len(urls)
    texts = scrape_many(urls, SCRAPE_WORKERS)

    accepted: list[tuple[int, str, str]] = []
    sublinks: list[str] = []

    def evaluate(url: str, text: str):
        if text.startswith("SCRAPE_ERROR"):
            stats["scrape_errors"] += 1
            return
        ok, reason = assess_tender_candidate(text)
        if ok:
            accepted.append((it_relevance_score(text), url, text))
        else:
            stats[f"rejected: {reason}"] += 1

    for url in urls:
        text = texts.get(url, "")
        if not text.startswith("SCRAPE_ERROR") and looks_like_listing_page(text, url):
            links = [l for l in discover_tender_links(url) if not _is_known(db, l)]
            if links:
                sublinks.extend(links)
                stats["listing_pages_expanded"] += 1
                continue
        evaluate(url, text)

    # 2e vague: détails extraits des pages listing
    sublinks = [l for l in dict.fromkeys(sublinks) if l not in texts][:MAX_LISTING_SUBLINKS]
    if sublinks:
        stats["urls_scraped"] += len(sublinks)
        for url, text in scrape_many(sublinks, SCRAPE_WORKERS).items():
            evaluate(url, text)

    accepted.sort(key=lambda x: x[0], reverse=True)
    created, seen = [], set()
    for _, url, text in accepted:
        norm = _normalize_url(url)
        if norm in seen or _is_known(db, url):
            continue
        seen.add(norm)
        tender = Tender(source="dynamic_search", source_url=norm, raw_text=text[:8000], status="new")
        db.add(tender)
        created.append(tender)
        if len(created) >= max_tenders:
            break

    db.commit()
    for t in created:
        db.refresh(t)
    stats["tenders_created"] += len(created)
    return created


def ingest_dynamic_tenders(db: Session, max_tenders: int = 15, results_per_query: int = 10,
                           time_filter: str | None = "qdr:m", queries: list[str] | None = None) -> list[Tender]:
    global _last_stats
    stats: Counter = Counter()
    queries = queries or build_queries(db)
    seen: set[str] = set()

    candidates = _collect_candidates(db, queries, results_per_query, time_filter, seen, stats)
    if len(candidates) < 15 and time_filter != "qdr:y":
        # élargit la fenêtre temporelle si la période courte est trop pauvre
        candidates += _collect_candidates(db, queries, results_per_query, "qdr:y", seen, stats)
        stats["time_window_relaxed"] = 1

    # Multi-source: liens issus directement des portails connus
    for url in discover_links_from_known_portals():
        norm = _normalize_url(url)
        if norm not in seen and not _is_known(db, url):
            seen.add(norm)
            candidates.append({"url": url, "title": "", "snippet": "tender appel d'offres"})
            stats["portal_links"] += 1

    stats["candidates_found"] = len(candidates)
    ranked = _prerank(candidates)
    stats["candidates_after_prerank"] = len(ranked)

    created = _ingest_urls(db, [c["url"] for c in ranked], max_tenders, stats)
    _last_stats = {"queries": queries, **dict(stats)}
    logger.info("Ingestion terminée: %s", _last_stats)
    return created


def ingest_from_portals(db: Session, max_tenders: int = 15) -> list[Tender]:
    global _last_stats
    stats: Counter = Counter()
    urls = [u for u in discover_links_from_known_portals() if not _is_known(db, u)]
    stats["portal_links"] = len(urls)
    created = _ingest_urls(db, urls, max_tenders, stats)
    _last_stats = dict(stats)
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
    tender.issuing_organization = fields["issuing_organization"]
    tender.sector = fields["sector"]
    tender.estimated_budget = fields["estimated_budget"]
    tender.deadline = fields["deadline"]
    tender.requirements = fields["requirements"]
    tender.summary = fields["summary"]
    tender.data_quality_flags = fields["quality_flags"]

    # Un tender trouvé automatiquement et jugé hors périmètre IT est écarté tôt.
    # Un tender saisi manuellement est toujours respecté.
    if tender.source == "dynamic_search" and not fields["is_relevant"]:
        tender.status = "rejected_irrelevant"
    else:
        tender.status = "extracted"

    db.commit()
    db.refresh(tender)
    return tender