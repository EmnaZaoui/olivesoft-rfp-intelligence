import json
import logging

from apify_client import ApifyClient

from app.config import settings

logger = logging.getLogger(__name__)


class ApifyUnavailable(RuntimeError):
    """Levée quand Apify n'est pas configuré (token absent)."""


def _client() -> ApifyClient:
    if not settings.apify_api_token:
        raise ApifyUnavailable("APIFY_API_TOKEN manquant dans backend/.env")
    return ApifyClient(settings.apify_api_token)


def run_actor(actor_id: str, run_input: dict, timeout_secs: int = 300) -> list[dict]:
    """Lance un acteur Apify, attend la fin, retourne les éléments du dataset."""
    client = _client()
    # Nouvelle API apify-client : pas de timeout_secs, run est un objet
    run = client.actor(actor_id).call(run_input=run_input)
    if not run:
        raise RuntimeError(f"Acteur {actor_id}: aucun run retourné")
    
    # run.status au lieu de run.get("status")
    status = getattr(run, "status", None) or (run.get("status") if hasattr(run, "get") else None)
    if status != "SUCCEEDED":
        raise RuntimeError(f"Acteur {actor_id} terminé avec le statut {status}")
    
    # run.default_dataset_id au lieu de run["defaultDatasetId"]
    dataset_id = getattr(run, "default_dataset_id", None) or (run.get("defaultDatasetId") if hasattr(run, "get") else None)
    if not dataset_id:
        raise RuntimeError(f"Acteur {actor_id}: pas de dataset ID")
    
    return list(client.dataset(dataset_id).iterate_items())


def search_google(queries: list[str], results_per_query: int = 10) -> list[dict]:
    """Google Search Scraper -> [{url, title, snippet}]. Réessaie sans pays si le code pays est refusé."""
    base = {
        "queries": "\n".join(queries),
        "maxPagesPerQuery": 1,
        "resultsPerPage": results_per_query,
        "languageCode": settings.apify_language_code,
        "mobileResults": False,
    }
    attempts = []
    if settings.apify_country_code:
        attempts.append({**base, "countryCode": settings.apify_country_code})
    attempts.append(base)

    items, last_error = None, None
    for run_input in attempts:
        try:
            items = run_actor(settings.apify_search_actor, run_input, timeout_secs=300)
            break
        except ApifyUnavailable:
            raise
        except Exception as e:
            last_error = e
            logger.warning("Recherche Apify échouée (%s), nouvelle tentative éventuelle", e)
    if items is None:
        raise RuntimeError(f"Recherche Apify impossible: {last_error}")

    results = []
    for page in items:
        for r in page.get("organicResults") or []:
            url = r.get("url") or r.get("link")
            if url:
                results.append({"url": url, "title": r.get("title", ""), "snippet": r.get("description", "")})
    return results


def crawl_pages(urls: list[str]) -> list[dict]:
    """Website Content Crawler (profondeur 0) -> [{url, title, text}] avec rendu JavaScript."""
    if not urls:
        return []
    run_input = {
        "startUrls": [{"url": u} for u in urls],
        "maxCrawlDepth": 0,
        "maxCrawlPages": len(urls),
        "crawlerType": "playwright:adaptive",
        "removeCookieWarnings": True,
    }
    items = run_actor(settings.apify_crawler_actor, run_input, timeout_secs=600)
    return [
        {
            "url": i.get("url", ""),
            "title": (i.get("metadata") or {}).get("title", ""),
            "text": " ".join((i.get("text") or "").split()),
        }
        for i in items if i.get("url")
    ]


def run_custom_actor() -> list[dict]:
    """
    Hook pour un acteur dédié aux appels d'offres trouvé dans l'Apify Store.
    Mappe les champs courants vers {url, title, snippet, text}.
    """
    if not settings.apify_custom_actor_id:
        return []
    try:
        run_input = json.loads(settings.apify_custom_actor_input or "{}")
    except json.JSONDecodeError:
        raise RuntimeError("APIFY_CUSTOM_ACTOR_INPUT n'est pas un JSON valide")

    out = []
    for item in run_actor(settings.apify_custom_actor_id, run_input, timeout_secs=600):
        url = item.get("url") or item.get("link") or item.get("tenderUrl") or item.get("sourceUrl")
        if not url:
            continue
        body = item.get("text") or item.get("description") or item.get("summary") or ""
        out.append({
            "url": url,
            "title": item.get("title") or item.get("name") or "",
            "snippet": str(body)[:400],
            "text": " ".join(str(body).split()),
        })
    return out