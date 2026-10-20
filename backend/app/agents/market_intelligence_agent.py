from app.agents.react_engine import run_react_agent

MAX_ITERATIONS = 5
MAX_CONSECUTIVE_FAILURES = 2

SYSTEM_PROMPT = """Tu es un agent de recherche autonome (pattern ReAct) qui construit le profil
d'un prospect (l'organisation qui a publié un appel d'offres) en utilisant un outil de recherche web.

Retourne UNIQUEMENT un JSON avec ce format exact:
{
  "thought": "raisonnement court",
  "action": "web_search" ou "finish",
  "action_input": "requête précise, incluant si possible le nom de l'organisation" ou "",
  "final_output": {
      "company_name": string,
      "sector": string,
      "estimated_revenue": string,
      "key_partners": [string],
      "past_projects": [string],
      "research_notes": string
  }
}

Règles:
- Base tes requêtes sur le nom de l'organisation fourni, pas uniquement sur un secteur générique.
- Ne finis jamais à la première itération sans avoir fait au moins une recherche.
- Si une recherche échoue, reformule avec des mots-clés différents.
- Passe à "finish" quand tu as au moins 2 informations concrètes, ou après plusieurs échecs.
- N'invente jamais un chiffre ou un partenaire non trouvé: utilise "unknown" plutôt que d'inventer
  (ce champ sera reformulé proprement en aval, tu n'as pas à t'en soucier).

Ne retourne jamais autre chose que ce JSON.
"""


def _default_profile(reason: str) -> dict:
    return {
        "company_name": "unknown", "sector": "unknown", "estimated_revenue": "unknown",
        "key_partners": [], "past_projects": [], "research_notes": f"Profil incomplet: {reason}",
    }


def run_market_intelligence_agent(organization_hint: str, tender_summary: str, tender_sector: str) -> dict:
    context_prompt = f"""
Organisation cible: {organization_hint or 'unknown'}
Secteur: {tender_sector}
Résumé de l'appel d'offres: {tender_summary}
"""
    seed_query = f"{organization_hint} secteur activité chiffre d'affaires partenaires"

    result = run_react_agent(
        system_prompt=SYSTEM_PROMPT,
        context_prompt=context_prompt,
        default_output_fn=_default_profile,
        seed_query=seed_query,
        max_iterations=MAX_ITERATIONS,
        max_consecutive_failures=MAX_CONSECUTIVE_FAILURES,
    )
    return {"profile": result["output"], "trace": result["trace"]}