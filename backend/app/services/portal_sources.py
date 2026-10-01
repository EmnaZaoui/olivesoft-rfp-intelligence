from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

from app.services.scraper_service import fetch_raw_html

DETAIL_URL_HINTS = ["appel-d-offre", "appel-offre", "tender", "rfp", "offre-", "-offres/"]


PORTAL_LISTING_URLS = [
    "https://www.j360.info/appels-d-offres/afrique/tunisie",
    "https://www.appeloffres.com/appels-offres/informatique-materiels-et-logiciels",
]

MIN_TITLE_LENGTH = 20
MAX_TITLE_LENGTH = 220
MAX_LINKS_PER_PORTAL = 8


def _is_probable_detail_link(href: str, text: str) -> bool:
    if not href or href.startswith("#") or href.startswith("javascript:"):
        return False
    if not (MIN_TITLE_LENGTH <= len(text.strip()) <= MAX_TITLE_LENGTH):
        return False

    lowered_href = href.lower()
    if any(hint in lowered_href for hint in DETAIL_URL_HINTS):
        return True

    # Heuristique générique: un slug long en fin d'URL est souvent une page de détail,
    # pas une simple page de catégorie.
    path = urlparse(href).path
    last_segment = path.strip("/").split("/")[-1]
    return len(last_segment) > 25


def discover_tender_links(listing_url: str) -> list[str]:
    """Récupère les liens vers des pages de détail depuis une page listing."""
    html = fetch_raw_html(listing_url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    candidates = []
    seen = set()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        text = a_tag.get_text(strip=True)

        if not _is_probable_detail_link(href, text):
            continue

        full_url = urljoin(listing_url, href)
        if full_url in seen:
            continue
        seen.add(full_url)
        candidates.append(full_url)

        if len(candidates) >= MAX_LINKS_PER_PORTAL:
            break

    return candidates


def discover_links_from_known_portals() -> list[str]:
    all_links = []
    for listing_url in PORTAL_LISTING_URLS:
        try:
            all_links.extend(discover_tender_links(listing_url))
        except Exception:
            continue  # un portail en panne ne doit pas bloquer les autres
    return all_links