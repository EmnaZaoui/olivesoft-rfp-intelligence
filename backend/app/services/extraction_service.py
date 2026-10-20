import re

from app.services.ollama_client import chat_json
from app.services.content_quality import extract_budget_hint, extract_deadline_hint

UNKNOWN_VALUES = {
    "", "unknown", "inconnu", "n/a", "na", "non précisé", "non precise", "non spécifié",
    "non specifie", "none", "null", "-", "non disponible", "not specified",
}

FOCUS_KEYWORDS = [
    "objet", "date limite", "délai", "exigence", "critère", "profil", "compétence",
    "expérience", "budget", "estimation", "livrable", "mission", "prestation",
    "conditions", "qualification", "deadline", "requirements", "scope", "dépôt",
]

REQUIREMENT_HINTS = re.compile(
    r"\b(doit|devra|doivent|exigé|exigée|exigées|exigés|expérience|maîtrise|certifi\w+|minimum|"
    r"compétence\w*|conformité|livrable\w*|intégration|sécurité|hébergement|formation|"
    r"maintenance|développement|migration|interopérabilité)\b",
    re.IGNORECASE,
)

EXTRACTION_SYSTEM_PROMPT = """Tu es un extracteur expert d'appels d'offres (RFP/tenders) IT.
Retourne UNIQUEMENT un objet JSON valide avec exactement ces champs:
{
  "is_it_software_tender": true ou false,
  "title": string,
  "issuing_organization": string,
  "sector": string,
  "estimated_budget": string,
  "deadline": string,
  "requirements": [string, ...],
  "summary": string
}

Règles:
- "is_it_software_tender" = true seulement si l'appel d'offres porte sur du développement logiciel,
  une plateforme web/mobile, un système d'information, de la data/IA ou de la transformation digitale.
- "issuing_organization" = l'entité qui PUBLIE l'appel d'offres (jamais le prestataire).
- "requirements" = 4 à 10 exigences concrètes (compétences, technologies, expérience, livrables,
  conformité), chacune courte (15 mots max).
- "deadline" = la date limite de remise des offres, telle qu'écrite dans le texte.
- Si une information n'est pas identifiable, mets "unknown" (ou [] pour requirements).
- N'invente jamais un chiffre ou une date. "summary": 2 à 3 phrases factuelles.

Exemple de sortie:
{
  "is_it_software_tender": true,
  "title": "Digitalisation des dossiers patients - hôpitaux publics",
  "issuing_organization": "Ministère de la Santé",
  "sector": "Santé publique",
  "estimated_budget": "250 000 TND",
  "deadline": "20 janvier 2027",
  "requirements": ["expérience en projets santé", "conformité RGPD", "équipe de 4 développeurs minimum"],
  "summary": "Le Ministère de la Santé souhaite digitaliser les dossiers patients. Budget de 250 000 TND, échéance au 20 janvier 2027."
}
Retourne uniquement le JSON.
"""

REQUIREMENTS_SYSTEM_PROMPT = """Tu analyses un appel d'offres IT. Liste les exigences techniques et
fonctionnelles que le prestataire doit satisfaire (technologies, expérience, compétences, livrables,
conformité, sécurité, délais). Si le texte décrit une mission sans exigences explicites, déduis les
compétences nécessaires pour la réaliser.
Retourne UNIQUEMENT: {"requirements": ["...", "..."]} avec 4 à 8 éléments courts (15 mots max).
"""


def _norm(value) -> str:
    if value is None:
        return "unknown"
    text = str(value).strip()
    return "unknown" if text.lower() in UNKNOWN_VALUES else text


def focus_text(raw: str, max_chars: int = 6000) -> str:
    """Pour les textes longs: garde le début + les fenêtres autour des mots-clés utiles."""
    if len(raw) <= max_chars:
        return raw
    lowered = raw.lower()
    windows = [(0, 1500)]
    for kw in FOCUS_KEYWORDS:
        for m in re.finditer(re.escape(kw), lowered):
            windows.append((max(0, m.start() - 200), min(len(raw), m.start() + 600)))
    windows.sort()
    merged = []
    for start, end in windows:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    out, size = [], 0
    for start, end in merged:
        chunk = raw[start:end]
        if size + len(chunk) > max_chars:
            chunk = chunk[: max_chars - size]
        out.append(chunk)
        size += len(chunk)
        if size >= max_chars:
            break
    return "\n...\n".join(out)


def _clean_requirements(items) -> list[str]:
    if not isinstance(items, list):
        items = [items] if items else []
    cleaned, seen = [], set()
    for item in items:
        if isinstance(item, dict):
            item = " ".join(str(v) for v in item.values())
        text = str(item).strip(" -•\t\n")
        key = text.lower()
        if len(text) < 6 or key in seen or key in UNKNOWN_VALUES:
            continue
        seen.add(key)
        cleaned.append(text[:200])
    return cleaned[:12]


def _mine_requirement_sentences(text: str, limit: int = 8) -> list[str]:
    sentences = re.split(r"[.;\n•]", text)
    picked = []
    for s in sentences:
        s = " ".join(s.split())
        if 25 <= len(s) <= 220 and REQUIREMENT_HINTS.search(s):
            picked.append(s)
        if len(picked) >= limit:
            break
    return picked


def _as_bool(value, default=True) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in ("false", "non", "no", "0")
    return default


def extract_tender_fields(raw_text: str) -> dict:
    flags: list[str] = []
    focused = focus_text(raw_text)

    try:
        result = chat_json(EXTRACTION_SYSTEM_PROMPT, focused)
    except ValueError:
        result = {}
        flags.append("Extraction LLM échouée: champs complétés par heuristiques.")

    fields = {
        "is_relevant": _as_bool(result.get("is_it_software_tender"), True),
        "title": _norm(result.get("title")),
        "issuing_organization": _norm(result.get("issuing_organization")),
        "sector": _norm(result.get("sector")),
        "estimated_budget": _norm(result.get("estimated_budget")),
        "deadline": _norm(result.get("deadline")),
        "summary": (result.get("summary") or "").strip(),
        "requirements": _clean_requirements(result.get("requirements")),
    }

    # --- Filets de sécurité par regex ---
    if fields["estimated_budget"] == "unknown":
        hint = extract_budget_hint(raw_text)
        if hint:
            fields["estimated_budget"] = hint
    if fields["deadline"] == "unknown":
        hint = extract_deadline_hint(raw_text)
        if hint:
            fields["deadline"] = hint

    # --- Exigences: passe dédiée -> heuristique -> dérivation ---
    if len(fields["requirements"]) < 3:
        try:
            second = chat_json(REQUIREMENTS_SYSTEM_PROMPT, focused)
            fields["requirements"] = _clean_requirements(fields["requirements"] + _clean_requirements(second.get("requirements")))
            flags.append("Exigences complétées par une 2e passe LLM dédiée.")
        except ValueError:
            pass

    if len(fields["requirements"]) < 3:
        mined = _mine_requirement_sentences(raw_text)
        fields["requirements"] = _clean_requirements(fields["requirements"] + mined)
        if mined:
            flags.append("Exigences complétées par extraction de phrases clés.")

    if not fields["requirements"]:
        base = f"{fields['title']}. {fields['summary']}".strip(". ")
        fields["requirements"] = [f"Réalisation de la mission: {base[:250]}"] if base else []
        flags.append("Aucune exigence explicite: exigence déduite du titre et du résumé.")

    # --- Valeurs de repli lisibles ---
    if fields["title"] == "unknown":
        fields["title"] = " ".join(raw_text.split())[:110]
        flags.append("Titre déduit du début du texte.")
    if not fields["summary"]:
        fields["summary"] = " ".join(focused.split())[:300]
        flags.append("Résumé déduit du texte brut.")

    for label, key in (("Budget", "estimated_budget"), ("Deadline", "deadline"),
                       ("Secteur", "sector"), ("Organisation émettrice", "issuing_organization")):
        if fields[key] == "unknown":
            flags.append(f"{label} non identifiable dans la source.")

    fields["quality_flags"] = flags
    return fields