from app.services.ollama_client import chat_json

METADATA_SYSTEM_PROMPT = """Tu extrais des métadonnées structurées d'un document interne OliveSoft
(CV ou fiche projet). Retourne UNIQUEMENT un JSON avec ce format exact:
{
  "document_category": "cv" ou "project" ou "reference",
  "person_name": string ou "unknown",
  "role": string ou "unknown",
  "years_experience": string ou "unknown",
  "key_skills": [string, ...],
  "client_name": string ou "unknown",
  "sector": string ou "unknown",
  "team_size": string ou "unknown",
  "duration": string ou "unknown",
  "budget": string ou "unknown",
  "technologies": [string, ...]
}

Règles:
- N'invente JAMAIS un chiffre absent du texte.
- "team_size", "duration" et "budget" doivent être des valeurs précises trouvées dans le texte
  (ex: "7 développeurs", "10 mois", "520 000 TND"), jamais des estimations.
- Retourne uniquement le JSON, sans texte avant ou après.
"""


def extract_document_metadata(content: str) -> dict:
    try:
        result = chat_json(METADATA_SYSTEM_PROMPT, content[:4000])
    except ValueError:
        result = {}

    defaults = {
        "document_category": "reference", "person_name": "unknown", "role": "unknown",
        "years_experience": "unknown", "key_skills": [], "client_name": "unknown",
        "sector": "unknown", "team_size": "unknown", "duration": "unknown",
        "budget": "unknown", "technologies": [],
    }
    for key, value in defaults.items():
        result.setdefault(key, value)
    return result