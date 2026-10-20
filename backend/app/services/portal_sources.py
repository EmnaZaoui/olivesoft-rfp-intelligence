from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

from app.services.scraper_service import fetch_raw_html
from app.services.content_quality import it_relevance_score, negative_score

DETAIL_URL_HINTS = ["appel-d-offre", "appel-offre", "tender", "rfp", "offre-", "-offres/", "consultation"]

# require_it_in_anchor=True: portail généraliste -> le texte du lien doit contenir un mot IT
PORTAL_SOURCES = [
    {"url": "https://www.j360.info/appels-d-offres/afrique/tunisie/?act=developpement-informatique",
     "require_it_in_anchor": False},
    {"url": "https://www.appeloffres.com/appels-offres/informatique-materiels-et-logiciels",
     "require_it_in_anchor": False},
]

MIN_TITLE_LENGTH = 20
MAX_TITLE_LENGTH = 260
MAX_LINKS_PER_PORTAL = 15


def _is_probable_detail_link(href: str, text: str, require_it: bool) -> bool:
    if not href or href.startswith("#") or href.startswith("javascript:") or href.startswith("mailto:"):
        return False
    text = text.strip()
    if not (MIN_TITLE_LENGTH <= len(text) <= MAX_TITLE_LENGTH):
        return False
    if negative_score(text) > 0 and it_relevance_score(text) == 0:
        return False
    if require_it and it_relevance_score(text) == 0:
        return False

    lowered_href = href.lower()
    if any(hint in lowered_href for hint in DETAIL_URL_HINTS):
        return True
    last_segment = urlparse(href).path.strip("/").split("/")[-1]
    return len(last_segment) > 25


def discover_tender_links(listing_url: str, require_it: bool = False) -> list[str]:
    html = fetch_raw_html(listing_url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    candidates, seen = [], set()
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        text = a_tag.get_text(strip=True)
        if not _is_probable_detail_link(href, text, require_it):
            continue
        full_url = urljoin(listing_url, href)
        if full_url in seen or full_url.rstrip("/") == listing_url.rstrip("/"):
            continue
        seen.add(full_url)
        candidates.append(full_url)
        if len(candidates) >= MAX_LINKS_PER_PORTAL:
            break
    return candidates


def discover_links_from_known_portals() -> list[str]:
    all_links: list[str] = []
    for source in PORTAL_SOURCES:
        try:
            all_links.extend(discover_tender_links(source["url"], source["require_it_in_anchor"]))
        except Exception:
            continue  
    return list(dict.fromkeys(all_links))