import logging
from collections import Counter
from datetime import datetime

import dateparser
import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.models import Tender
from app.services.extraction_service import extract_tender_fields
from app.services.content_quality import it_relevance_score, negative_score

logger = logging.getLogger(__name__)

WORLDBANK_URL = "https://search.worldbank.org/api/v2/procnotices"
WORLDBANK_DETAIL = "https://projects.worldbank.org/en/projects-operations/procurement-detail/{id}"

SEARCH_TERMS = [
    "software development", "information system", "web application", "digital platform",
    "mobile application", "e-government", "ERP", "data platform", "IT consulting services",
]

_last_stats: dict = {}


def get_last_opendata_stats() -> dict:
    return _last_stats


def _html_to_text(value: str) -> str:
    return " ".join(BeautifulSoup(value or "", "html.parser").get_text(" ").split())


def _parse_deadline(value: str | None):
    if not value:
        return None
    parsed = dateparser.parse(value)
    return parsed.replace(tzinfo=None) if parsed else None


def _fetch_worldbank(term: str, rows: int = 40) -> list[dict]:
    params = {"format": "json", "qterm": term, "rows": rows, "srt": "submission_deadline_date", "order": "desc"}
    response = requests.get(WORLDBANK_URL, params=params, timeout=30)
    response.raise_for_status()
    notices = response.json().get("procnotices", [])
    return notices if isinstance(notices, list) else list(notices.values())


def ingest_opendata(db: Session, max_tenders: int = 10, country: str = "") -> list[Tender]:
    """Avis de marchés réels (Banque mondiale), structurés: deadline, référence, texte complet."""
    global _last_stats
    stats: Counter = Counter()
    now = datetime.utcnow()
    candidates, seen_ids = [], set()

    for term in SEARCH_TERMS:
        try:
            notices = _fetch_worldbank(term)
        except Exception as e:
            stats["api_errors"] += 1
            stats["last_error"] = str(e)[:150]
            continue
        for n in notices:
            nid = str(n.get("id") or n.get("bid_reference_no") or "")
            if not nid or nid in seen_ids:
                continue
            seen_ids.add(nid)
            stats["raw_notices"] += 1

            deadline = _parse_deadline(n.get("submission_deadline_date"))
            if not deadline or deadline < now:
                stats["rejected: deadline dépassée ou absente"] += 1
                continue
            if country and country.lower() not in str(n.get("project_ctry_name", "")).lower():
                stats["rejected: pays différent"] += 1
                continue

            body = _html_to_text(n.get("notice_text") or "")
            text = (
                f"Titre: {n.get('bid_description') or n.get('notice_title') or ''}\n"
                f"Organisation: {n.get('contact_organization') or n.get('project_name') or ''}\n"
                f"Pays: {n.get('project_ctry_name', '')}\n"
                f"Référence: {n.get('bid_reference_no', '')}\n"
                f"Type d'avis: {n.get('notice_type', '')}\n"
                f"Date limite de remise des offres: {deadline.strftime('%d/%m/%Y')}\n\n{body}"
            )
            it = it_relevance_score(text)
            if it < 3 or negative_score(text) >= it:
                stats["rejected: hors périmètre IT"] += 1
                continue
            candidates.append((it, nid, deadline, n, text))

    candidates.sort(key=lambda c: c[0], reverse=True)
    stats["candidates_it"] = len(candidates)

    created: list[Tender] = []
    for _, nid, deadline, n, text in candidates:
        if len(created) >= max_tenders:
            break
        url = WORLDBANK_DETAIL.format(id=nid)
        if db.query(Tender.id).filter(Tender.source_url == url).first():
            stats["already_known"] += 1
            continue
        try:
            fields = extract_tender_fields(text[:7000])
        except Exception:
            stats["extraction_error"] += 1
            continue
        if not fields["is_relevant"]:
            stats["rejected: jugé hors périmètre IT par le LLM"] += 1
            continue

        tender = Tender(
            source="worldbank_api", source_url=url, raw_text=text[:8000], status="extracted",
            title=fields["title"], issuing_organization=fields["issuing_organization"],
            sector=fields["sector"], estimated_budget=fields["estimated_budget"],
            deadline=deadline.strftime("%d/%m/%Y"),  # deadline fiable fournie par l'API
            requirements=fields["requirements"], summary=fields["summary"],
            data_quality_flags=fields["quality_flags"],
        )
        db.add(tender)
        db.commit()
        db.refresh(tender)
        created.append(tender)

    stats["tenders_created"] = len(created)
    _last_stats = dict(stats)
    return created