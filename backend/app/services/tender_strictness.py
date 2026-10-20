import re
from urllib.parse import urlparse

from app.services.content_quality import it_relevance_score, negative_score, is_probably_expired

NON_TENDER_URL_PARTS = (
    "conditions", "mentions-legales", "mentions_legales", "politique", "privacy", "cookies",
    "contact", "login", "connexion", "inscription", "faq", "a-propos", "about", "sitemap",
    "plan-du-site", "cgu", "cgv", "terms", "emploi", "recrutement", "carriere", "career", "jobs",
)

# 4 familles de signaux: un vrai avis d'appel d'offres en contient au moins 2
SIGNAL_GROUPS = {
    "echeance": re.compile(
        r"date limite|dernier délai|délai de (?:dépôt|remise|réception)|remise des offres|"
        r"dépôt des offres|clôture|closing date|submission deadline|deadline", re.I),
    "dossier": re.compile(
        r"cahier des (?:charges|clauses)|dossier d.appel d.offres|termes de référence|"
        r"terms of reference|\btdr\b|\bdao\b", re.I),
    "objet": re.compile(
        r"objet (?:de l.appel|du march|de la consultation|de l.avis)|avis d.appel d.offres|"
        r"appel d.offres (?:n°|no\b|num)|consultation (?:n°|no\b)|\brfp\b|request for proposal|"
        r"invitation to (?:tender|bid)|call for (?:tenders|proposals)", re.I),
    "soumission": re.compile(
        r"soumissionnaire|caution(?:nement)? provisoire|\bplis?\b|offre technique|offre financière|"
        r"technical proposal|financial proposal|bidder", re.I),
}


def is_non_tender_url(url: str) -> bool:
    parsed = urlparse(url.lower())
    target = parsed.path + "?" + parsed.query
    return any(part in target for part in NON_TENDER_URL_PARTS)


def tender_signal_count(text: str) -> int:
    return sum(1 for rx in SIGNAL_GROUPS.values() if rx.search(text))


def assess_strict(text: str, url: str, min_signals: int = 2) -> tuple[bool, str, int]:
    """Retourne (ok, raison, nb_signaux). Plus exigeant que assess_tender_candidate."""
    if is_non_tender_url(url):
        return False, "page non appel d'offres (URL)", 0
    if not text or text.startswith(("SCRAPE_ERROR", "PDF_EXTRACTION_ERROR")):
        return False, "contenu illisible", 0
    if len(text) < 600:
        return False, "contenu trop court", 0

    signals = tender_signal_count(text)
    if signals < min_signals:
        return False, "signaux d'appel d'offres insuffisants", signals

    it_score = it_relevance_score(text)
    if it_score < 3:
        return False, "hors périmètre IT", signals
    if negative_score(text) >= it_score:
        return False, "domaine non IT dominant", signals
    if is_probably_expired(text):
        return False, "deadline dépassée", signals
    return True, "ok", signals