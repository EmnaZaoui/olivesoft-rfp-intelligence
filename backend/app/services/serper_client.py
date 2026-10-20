import requests
from urllib.parse import urlparse

from app.config import settings

SERPER_URL = "https://google.serper.dev/search"

# Domaines qui ne contiennent jamais d'appels d'offres exploitables
NOISE_DOMAINS = (
    "facebook.com", "linkedin.com", "youtube.com", "twitter.com", "x.com",
    "instagram.com", "wikipedia.org", "pinterest.com", "tiktok.com", "reddit.com",
    "indeed.com", "glassdoor.com", "tanitjobs.com", "keejob.com", "emploi.nat.tn",
)


def is_noise_domain(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(host == d or host.endswith("." + d) for d in NOISE_DOMAINS)


def search_web(
    query: str,
    num_results: int = 5,
    country: str = "tn",
    language: str = "fr",
    time_filter: str | None = None,
    page: int = 1,
    filter_noise: bool = False,
) -> list[dict]:
    """
    time_filter: format Google 'tbs' (ex: 'qdr:w' semaine, 'qdr:m' mois, 'qdr:y' année).
    filter_noise: écarte réseaux sociaux / sites d'emploi (utile pour la détection de tenders,
    à laisser à False pour la recherche d'informations sur une entreprise).
    """
    headers = {"X-API-KEY": settings.serper_api_key, "Content-Type": "application/json"}
    payload = {"q": query, "num": num_results, "gl": country, "hl": language}
    if time_filter:
        payload["tbs"] = time_filter
    if page > 1:
        payload["page"] = page

    try:
        response = requests.post(SERPER_URL, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
    except requests.RequestException as e:
        return [{"title": "ERROR", "link": "", "snippet": f"Erreur Serper API: {e}"}]

    data = response.json()
    results = [
        {
            "title": item.get("title", ""),
            "link": item.get("link", ""),
            "snippet": item.get("snippet", ""),
        }
        for item in data.get("organic", [])[:num_results]
    ]
    if filter_noise:
        results = [r for r in results if r["link"] and not is_noise_domain(r["link"])]
    return results