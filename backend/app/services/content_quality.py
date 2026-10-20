import re
from datetime import datetime

import dateparser

TENDER_KEYWORDS = [
    "appel d'offre", "appel d'offres", "appel d’offre", "appel d’offres", "cahier des charges",
    "tender", "rfp", "request for proposal", "date limite", "deadline", "consultation",
    "marché public", "soumission", "dépôt des offres", "remise des offres", "call for proposals",
]

IT_KEYWORDS = [
    "développement", "developpement", "logiciel", "application", "web", "mobile", "plateforme",
    "système d'information", "systeme d'information", "informatique", "erp", "digital",
    "digitalisation", "numérique", "software", "portail", "site web", "base de données",
    "cloud", "api", "intelligence artificielle", "développeur", "maintenance applicative",
    "refonte", "gestion électronique", "ged", "business intelligence", "data", "react",
    "java", "python", ".net", "php", "angular", "devops", "saas", "e-commerce", "crm",
    "development", "information system", "digital transformation",
]

NEGATIVE_KEYWORDS = [
    "travaux de construction", "génie civil", "btp", "gardiennage", "nettoyage",
    "restauration", "médicaments", "mobilier", "véhicules", "carburant", "bâtiment",
    "voirie", "recrutement", "offre d'emploi", "offre d’emploi", "cdi", "cdd", "stage",
    "fourniture de denrées", "assainissement", "terrassement",
]

_IT_PATTERNS = [re.compile(r"(?<!\w)" + re.escape(k) + r"(?!\w)", re.I) for k in IT_KEYWORDS]
_NEG_PATTERNS = [re.compile(r"(?<!\w)" + re.escape(k) + r"(?!\w)", re.I) for k in NEGATIVE_KEYWORDS]

CURRENCY_REGEX = re.compile(
    r"(\d[\d\s.,]{2,})\s?(TND|DT|dinars?|€|EUR|USD|\$|MAD|DA)", re.IGNORECASE
)

_MONTHS_FR = "janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre"
_MONTHS_EN = "january|february|march|april|may|june|july|august|september|october|november|december"

DATE_PATTERN = (
    r"\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}"
    rf"|\d{{1,2}}(?:er)?\s+(?:{_MONTHS_FR})\s+\d{{4}}"
    rf"|(?:{_MONTHS_EN})\s+\d{{1,2}},?\s+\d{{4}}"
    rf"|\d{{1,2}}\s+(?:{_MONTHS_EN})\s+\d{{4}}"
)
DATE_REGEX = re.compile(DATE_PATTERN, re.IGNORECASE)

DEADLINE_CONTEXT_REGEX = re.compile(
    r"(?:date limite|délai de (?:dépôt|remise|réception)|avant le|au plus tard|clôture|cloture|"
    r"deadline|closing date|dépôt des offres|remise des offres|submission)"
    r"\D{0,80}?(?P<date>" + DATE_PATTERN + r")",
    re.IGNORECASE,
)


def content_has_tender_signal(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in TENDER_KEYWORDS)


def it_relevance_score(text: str) -> int:
    """Nombre de mots-clés IT distincts présents dans le texte."""
    return sum(1 for p in _IT_PATTERNS if p.search(text))


def negative_score(text: str) -> int:
    return sum(1 for p in _NEG_PATTERNS if p.search(text))


def looks_like_listing_page(text: str, url: str = "", occurrence_threshold: int = 6) -> bool:
    """
    Une page listing répète le motif 'appel d'offre' ET contient beaucoup de dates
    (une par annonce). Une page de détail peut citer 'appel d'offre' souvent mais a peu de dates.
    """
    lowered = text.lower()
    count = (
        lowered.count("appel d'offre") + lowered.count("appel d’offre") + lowered.count("tender")
    )
    dates = len(DATE_REGEX.findall(text))
    if count >= occurrence_threshold and dates >= 4:
        return True
    if url and any(x in url.lower() for x in ("?act=", "/categorie", "/category", "?page=", "/liste")) and count >= 3:
        return True
    return False


def extract_budget_hint(text: str) -> str | None:
    match = CURRENCY_REGEX.search(text)
    return match.group(0).strip() if match else None


def _parse_date(raw: str):
    parsed = dateparser.parse(raw, languages=["fr", "en"], settings={"DATE_ORDER": "DMY"})
    return parsed.replace(tzinfo=None) if parsed else None


def find_deadline_candidates(text: str) -> list[tuple[datetime, str]]:
    """Dates trouvées à proximité de mots du type 'date limite', 'avant le', 'deadline'."""
    found = []
    for m in DEADLINE_CONTEXT_REGEX.finditer(text):
        raw = m.group("date")
        parsed = _parse_date(raw)
        if parsed:
            found.append((parsed, raw))
    return found


def extract_deadline_hint(text: str) -> str | None:
    candidates = find_deadline_candidates(text)
    if candidates:
        now = datetime.utcnow()
        future = [c for c in candidates if c[0] >= now]
        chosen = min(future, key=lambda c: c[0]) if future else max(candidates, key=lambda c: c[0])
        return chosen[1].strip()
    match = DATE_REGEX.search(text)
    return match.group(0).strip() if match else None


def is_probably_expired(text: str) -> bool:
    candidates = find_deadline_candidates(text)
    if not candidates:
        return False
    now = datetime.utcnow()
    return all(d < now for d, _ in candidates)


def is_content_sufficient(text: str, min_length: int = 400) -> bool:
    if not text:
        return False
    if text.startswith("SCRAPE_ERROR") or text.startswith("PDF_EXTRACTION_ERROR"):
        return False
    if len(text) < min_length:
        return False
    return content_has_tender_signal(text)


def assess_tender_candidate(text: str) -> tuple[bool, str]:
    """Décide si un contenu scrapé mérite de devenir un tender. Retourne (ok, raison)."""
    if not is_content_sufficient(text, min_length=300):
        return False, "contenu insuffisant ou sans signal d'appel d'offres"
    it_score = it_relevance_score(text)
    if it_score < 2:
        return False, "hors périmètre IT"
    if negative_score(text) > it_score:
        return False, "domaine non IT dominant (BTP, emploi, fournitures...)"
    if is_probably_expired(text):
        return False, "deadline dépassée"
    return True, "ok"