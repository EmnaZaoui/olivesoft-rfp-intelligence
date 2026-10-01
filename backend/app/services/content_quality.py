import re

TENDER_KEYWORDS = [
    "appel d'offre", "appel d'offres", "cahier des charges", "tender",
    "rfp", "request for proposal", "date limite", "deadline", "consultation",
    "marché public", "soumission",
]

CURRENCY_REGEX = re.compile(
    r"(\d[\d\s.,]{2,})\s?(TND|DT|dinars?|€|EUR|USD|\$|MAD|DA)", re.IGNORECASE
)

DATE_REGEX = re.compile(
    r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})|"
    r"(\d{1,2}\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4})",
    re.IGNORECASE,
)


def content_has_tender_signal(text: str) -> bool:
    """Vérifie qu'un minimum de vocabulaire d'appel d'offres est présent."""
    lowered = text.lower()
    return any(keyword in lowered for keyword in TENDER_KEYWORDS)


def looks_like_listing_page(text: str, occurrence_threshold: int = 4) -> bool:
    """
    Une page 'listing/catégorie' répète le motif 'appel d'offre' de nombreuses fois
    (une occurrence par élément listé), contrairement à une page de détail qui n'en
    parle qu'une fois, dans son propre contexte.
    """
    lowered = text.lower()
    count = (
        lowered.count("appel d'offre")
        + lowered.count("appel d'offres")
        + lowered.count("tender")
    )
    return count >= occurrence_threshold


def extract_budget_hint(text: str) -> str | None:
    match = CURRENCY_REGEX.search(text)
    if match:
        return match.group(0).strip()
    return None


def extract_deadline_hint(text: str) -> str | None:
    match = DATE_REGEX.search(text)
    if match:
        return match.group(0).strip()
    return None


def is_content_sufficient(text: str, min_length: int = 400) -> bool:
    """Filtre les contenus trop pauvres, vides, ou en erreur avant de créer un tender."""
    if not text:
        return False
    if text.startswith("SCRAPE_ERROR") or text.startswith("PDF_EXTRACTION_ERROR"):
        return False
    if len(text) < min_length:
        return False
    return content_has_tender_signal(text)