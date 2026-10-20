import logging
from collections import Counter
from datetime import datetime

import dateparser
from sqlalchemy.orm import Session

from app.models import Tender
from app.services import apify_client_service as apify
from app.services.serper_client import is_noise_domain
from app.services.search_queries import build_queries
from app.services.portal_sources import discover_tender_links, discover_links_from_known_portals
from app.services.scraper_service import scrape_many
from app.services.extraction_service import extract_tender_fields
from app.services.content_quality import looks_like_listing_page, it_relevance_score
from app.services.tender_strictness import assess_strict, is_non_tender_url
from app.services.tender_detection_service import _normalize_url, _is_known, _prerank
from app.services.notice_classifier import assess_real_notice

logger = logging.getLogger(__name__)

MAX_QUERIES = 8
MAX_PAGES_TO_CRAWL = 25
MAX_LISTING_SUBLINKS = 15

_last_stats: dict = {}


def get_last_apify_stats() -> dict:
    return _last_stats


def _deadline_expired(deadline_text: str | None) -> bool:
    if not deadline_text or deadline_text.lower() == "unknown":
        return False
    parsed = dateparser.parse(deadline_text, languages=["fr", "en"], settings={"DATE_ORDER": "DMY"})
    return bool(parsed and parsed.replace(tzinfo=None) < datetime.utcnow())


def _fetch_texts(candidates: list[dict], stats: Counter) -> dict[str, str]:
    """Texte par URL normalisée: texte déjà fourni -> Apify crawler -> scraper local en secours."""
    texts: dict[str, str] = {}
    to_crawl = []
    for c in candidates:
        if len(c.get("text", "")) >= 600:
            texts[_normalize_url(c["url"])] = c["text"]
        elif not c["url"].lower().split("?")[0].endswith(".pdf"):
            to_crawl.append(c["url"])

    if to_crawl:
        try:
            for item in apify.crawl_pages(to_crawl):
                texts[_normalize_url(item["url"])] = item["text"]
            stats["pages_crawled_apify"] += len(to_crawl)
        except apify.ApifyUnavailable:
            raise
        except Exception as e:
            stats["apify_crawl_error"] = str(e)[:200]

    missing = [c["url"] for c in candidates if len(texts.get(_normalize_url(c["url"]), "")) < 300]
    if missing:
        stats["local_fallback"] += len(missing)
        for url, text in scrape_many(missing, 4).items():
            texts[_normalize_url(url)] = text
    return texts


def ingest_with_apify(db: Session, max_tenders: int = 10, pre_extract: bool = True,
                      source: str = "google", queries: list[str] | None = None) -> list[Tender]:
    """
    source: google | custom | both.
    pre_extract: extrait AVANT d'enregistrer; seuls les tenders IT et non expirés entrent en base.
    """
    global _last_stats
    stats: Counter = Counter()
    queries = (queries or build_queries(db))[:MAX_QUERIES]

    raw: list[dict] = []
    if source in ("google", "both"):
        try:
            raw += apify.search_google(queries)
        except apify.ApifyUnavailable:
            raise
        except Exception as e:
            stats["google_search_error"] = str(e)[:200]
    if source in ("custom", "both"):
        try:
            raw += apify.run_custom_actor()
        except apify.ApifyUnavailable:
            raise
        except Exception as e:
            stats["custom_actor_error"] = str(e)[:200]
    stats["raw_results"] = len(raw)

    # Multi-source: liens des portails connus
    for url in discover_links_from_known_portals():
        raw.append({"url": url, "title": "", "snippet": "tender appel d'offres"})
        stats["portal_links"] += 1

    # --- Pré-filtrage des candidats ---
    seen: set[str] = set()
    candidates = []
    for r in raw:
        url = r["url"]
        norm = _normalize_url(url)
        if norm in seen:
            continue
        seen.add(norm)
        if is_noise_domain(url) or is_non_tender_url(url):
            stats["rejected: domaine ou URL non pertinent"] += 1
            continue
        if _is_known(db, url):
            stats["already_known"] += 1
            continue
        candidates.append(r)

    ranked = _prerank(candidates)[:MAX_PAGES_TO_CRAWL]
    stats["candidates_to_fetch"] = len(ranked)

    texts = _fetch_texts(ranked, stats)

    accepted: list[tuple[int, str, str]] = []
    sublinks: list[str] = []

    def evaluate(url: str, text: str, allow_expand: bool):
        if looks_like_listing_page(text, url):
            if allow_expand:
                sublinks.extend(l for l in discover_tender_links(url) if not _is_known(db, l))
                stats["listing_pages_expanded"] += 1
            else:
                stats["rejected: page listing"] += 1
            return
        ok, reason, signals = assess_strict(text, url)
        if ok:
            ok, reason = assess_real_notice(text, url)
        if ok:
            accepted.append((signals * 3 + it_relevance_score(text), url, text))
        else:
            stats[f"rejected: {reason}"] += 1

    for c in ranked:
        evaluate(c["url"], texts.get(_normalize_url(c["url"]), ""), allow_expand=True)

    # 2e vague: pages de détail issues des listings
    sub = [{"url": u} for u in dict.fromkeys(sublinks) if _normalize_url(u) not in seen][:MAX_LISTING_SUBLINKS]
    if sub:
        for c in sub:
            seen.add(_normalize_url(c["url"]))
        sub_texts = _fetch_texts(sub, stats)
        for c in sub:
            evaluate(c["url"], sub_texts.get(_normalize_url(c["url"]), ""), allow_expand=False)

    stats["accepted_by_strict_filter"] = len(accepted)

    # --- Création (avec extraction préalable) ---
    accepted.sort(key=lambda x: x[0], reverse=True)
    created: list[Tender] = []
    attempts = 0
    for _, url, text in accepted:
        if len(created) >= max_tenders or attempts >= max_tenders * 2:
            break
        if _is_known(db, url):
            continue
        attempts += 1

        tender = Tender(source="apify_search", source_url=_normalize_url(url),
                        raw_text=text[:8000], status="new")
        if pre_extract:
            try:
                fields = extract_tender_fields(text)
            except Exception as e:
                stats["extraction_error"] += 1
                logger.warning("Extraction échouée pour %s: %s", url, e)
                continue
            if not fields["is_relevant"]:
                stats["rejected: jugé hors périmètre IT par le LLM"] += 1
                continue
            if _deadline_expired(fields["deadline"]):
                stats["rejected: deadline dépassée (après extraction)"] += 1
                continue
            if (fields["deadline"] or "unknown").lower() == "unknown":
                stats["rejected: pas de deadline après extraction"] += 1
                continue
            tender.title = fields["title"]
            tender.issuing_organization = fields["issuing_organization"]
            tender.sector = fields["sector"]
            tender.estimated_budget = fields["estimated_budget"]
            tender.deadline = fields["deadline"]
            tender.requirements = fields["requirements"]
            tender.summary = fields["summary"]
            tender.data_quality_flags = fields["quality_flags"]
            tender.status = "extracted"

        db.add(tender)
        db.commit()
        db.refresh(tender)
        created.append(tender)

    stats["tenders_created"] = len(created)
    _last_stats = {"queries": queries, "source": source, **dict(stats)}
    logger.info("Ingestion Apify terminée: %s", _last_stats)
    return created