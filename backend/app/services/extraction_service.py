from app.services.ollama_client import chat_json
from app.services.content_quality import extract_budget_hint, extract_deadline_hint

EXTRACTION_SYSTEM_PROMPT = """Tu es un extracteur expert d'informations pour des appels d'offres (RFP/tenders).
Analyse le texte fourni et retourne UNIQUEMENT un objet JSON valide avec exactement ces champs:
{
  "title": string,
  "issuing_organization": string,
  "sector": string,
  "estimated_budget": string,
  "deadline": string,
  "requirements": [string, ...],
  "summary": string
}

Règles:
- "issuing_organization" = l'entité qui publie l'appel d'offres (ministère, entreprise, banque...), jamais le prestataire.
- Si une information n'est vraiment pas identifiable dans le texte, mets "unknown" (ou [] pour requirements).
- N'invente jamais un chiffre ou une date absente du texte.
- "summary" doit faire 2 à 3 phrases factuelles.

Exemple d'entrée:
"Le Ministère de la Santé lance un appel d'offres pour la digitalisation des dossiers patients dans
les hôpitaux publics. Budget: 250 000 TND. Date limite: 20 janvier 2027. Exigences: expérience santé,
conformité RGPD, équipe de 4 développeurs minimum."

Exemple de sortie attendue:
{
  "title": "Digitalisation des dossiers patients - hôpitaux publics",
  "issuing_organization": "Ministère de la Santé",
  "sector": "Santé publique",
  "estimated_budget": "250 000 TND",
  "deadline": "20 janvier 2027",
  "requirements": ["expérience santé", "conformité RGPD", "équipe de 4 développeurs minimum"],
  "summary": "Le Ministère de la Santé souhaite digitaliser les dossiers patients dans les hôpitaux publics. Le budget est de 250 000 TND avec une échéance au 20 janvier 2027."
}

Retourne uniquement le JSON, sans aucun texte avant ou après.
"""


def extract_tender_fields(raw_text: str) -> dict:
    result = chat_json(EXTRACTION_SYSTEM_PROMPT, raw_text)

    result.setdefault("title", "unknown")
    result.setdefault("issuing_organization", "unknown")
    result.setdefault("sector", "unknown")
    result.setdefault("estimated_budget", "unknown")
    result.setdefault("deadline", "unknown")
    result.setdefault("requirements", [])
    result.setdefault("summary", "")

    if not isinstance(result["requirements"], list):
        result["requirements"] = [str(result["requirements"])]

    # Filet de sécurité: si le LLM local n'a pas trouvé budget/deadline,
    # on tente une détection par regex directement sur le texte source.
    if result["estimated_budget"] in ("unknown", "", None):
        hint = extract_budget_hint(raw_text)
        if hint:
            result["estimated_budget"] = hint

    if result["deadline"] in ("unknown", "", None):
        hint = extract_deadline_hint(raw_text)
        if hint:
            result["deadline"] = hint

    return result