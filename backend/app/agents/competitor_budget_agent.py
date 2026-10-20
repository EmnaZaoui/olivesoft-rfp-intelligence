from app.agents.react_engine import run_react_agent

MAX_ITERATIONS = 4
MAX_CONSECUTIVE_FAILURES = 2

SYSTEM_PROMPT = """Tu es un agent d'analyse concurrentielle et budgétaire (pattern ReAct) pour
une société de services IT (OliveSoft) qui évalue un appel d'offres.

Retourne UNIQUEMENT un JSON avec ce format exact:
{
  "thought": "raisonnement court",
  "action": "web_search" ou "finish",
  "action_input": "requête précise" ou "",
  "final_output": {
      "estimated_budget_range": string (ex: "400 000 - 600 000 TND"),
      "confidence": "low" ou "medium" ou "high",
      "competitive_positioning": string (2-3 phrases sur comment se positionner),
      "likely_competitors": [string],
      "notes": string
  }
}

Règles:
- Cherche des informations sur des projets similaires, des fourchettes de prix pratiquées dans
  ce secteur/pays, et des sociétés concurrentes probables sur ce type de marché.
- Si l'information est incertaine, indique "confidence": "low" plutôt que d'inventer une précision.
- Passe à "finish" après avoir obtenu une estimation raisonnable ou après plusieurs échecs.

Ne retourne jamais autre chose que ce JSON.
"""


def _default_output(reason: str) -> dict:
    return {
        "estimated_budget_range": "unknown", "confidence": "low",
        "competitive_positioning": f"Analyse incomplète: {reason}",
        "likely_competitors": [], "notes": reason,
    }


def run_competitor_budget_agent(title: str, sector: str, estimated_budget: str, summary: str) -> dict:
    context_prompt = f"""
Titre du tender: {title}
Secteur: {sector}
Budget déjà connu (peut être "unknown"): {estimated_budget}
Résumé: {summary}
"""
    seed_query = f"{sector} prix moyen projet logiciel similaire {title}"

    result = run_react_agent(
        system_prompt=SYSTEM_PROMPT,
        context_prompt=context_prompt,
        default_output_fn=_default_output,
        seed_query=seed_query,
        max_iterations=MAX_ITERATIONS,
        max_consecutive_failures=MAX_CONSECUTIVE_FAILURES,
    )
    return {"output": result["output"], "trace": result["trace"]}