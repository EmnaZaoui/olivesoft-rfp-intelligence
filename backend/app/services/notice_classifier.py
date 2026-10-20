import re
from datetime import datetime

from app.services.ollama_client import chat_json
from app.services.content_quality import find_deadline_candidates

BLOG_URL_PARTS = (
    "blog", "ressource", "resources", "guide", "article", "actualit", "news", "conseil",
    "tips", "comment-", "how-to", "formation", "definition", "magazine", "presse", "press",
    "cabinet", "agence", "services/", "solutions/",
)

BLOG_TITLE_RX = re.compile(
    r"^(comment|how to|guide|conseils?|astuces?|pourquoi|qu.est-ce|tout savoir|réussir|répondre à|"
    r"\d+\s+(étapes|conseils|raisons|erreurs))", re.I)

BLOG_TEXT_RX = re.compile(
    r"nos services|contactez-nous|notre équipe|nos experts|abonnez-vous|newsletter|lire aussi|"
    r"articles similaires|partager cet article|vous devez|vous pouvez|étape \d|"
    r"nous vous accompagnons|demander un devis|prendre rendez-vous|télécharger le guide|"
    r"à lire aussi|publié le|temps de lecture", re.I)

REFERENCE_RX = re.compile(
    r"(?:\bAO\b|appel d.offres|consultation|r[ée]f(?:[ée]rence)?|\bn°|\bno\.?)\s*[:\-]?\s*"
    r"[A-Z]{0,6}\s?\d{1,5}\s*[/\-]\s*\d{2,4}", re.I)

CLASSIFIER_PROMPT = """Tu classes un document web. Retourne UNIQUEMENT:
{"document_type": "tender_notice" | "guide_or_article" | "listing" | "company_page" | "other",
 "reason": "une phrase"}

Définitions strictes:
- tender_notice = un avis/dossier d'appel d'offres REEL publié par un acheteur précis: objet précis,
  date limite précise, conditions de soumission. C'est un document que le prestataire doit satisfaire.
- guide_or_article = blog, conseils, tutoriel, définition, actualité qui PARLE des appels d'offres
  sans en être un.
- listing = page qui liste plusieurs annonces.
- company_page = page de présentation d'une société ou de ses services.
Un texte qui donne des conseils pour répondre à des appels d'offres est TOUJOURS guide_or_article.
"""


def has_future_deadline(text: str) -> bool:
    now = datetime.utcnow()
    return any(d >= now for d, _ in find_deadline_candidates(text))


def looks_like_blog(text: str, url: str) -> tuple[bool, str]:
    lowered = url.lower()
    if any(p in lowered for p in BLOG_URL_PARTS):
        return True, "URL de type blog/ressource/guide"
    head = text[:200].strip()
    if BLOG_TITLE_RX.search(head):
        return True, "titre de type guide/article"
    hits = len(BLOG_TEXT_RX.findall(text))
    if hits >= 3:
        return True, f"vocabulaire éditorial/commercial ({hits} marqueurs)"
    return False, ""


def assess_real_notice(text: str, url: str, require_deadline: bool = True) -> tuple[bool, str]:
    """Preuves concrètes qu'un contenu est un VRAI avis d'appel d'offres."""
    blog, why = looks_like_blog(text, url)
    if blog:
        return False, f"article/blog écarté: {why}"

    future = has_future_deadline(text)
    reference = bool(REFERENCE_RX.search(text))
    if require_deadline and not future:
        return False, "aucune date limite future identifiable"
    if not require_deadline and not (future or reference):
        return False, "ni date limite ni référence d'appel d'offres"

    try:
        verdict = chat_json(CLASSIFIER_PROMPT, text[:2500])
    except ValueError:
        # LLM indisponible: les preuves déterministes ci-dessus suffisent
        return True, "ok (classifieur LLM indisponible)"

    doc_type = str(verdict.get("document_type", "")).strip().lower()
    if doc_type != "tender_notice":
        return False, f"classé '{doc_type or 'inconnu'}' par le LLM"
    return True, "ok"