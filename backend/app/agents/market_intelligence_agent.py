from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END

from app.services.ollama_client import chat_json
from app.agents.mcp_client import call_mcp_tool

MAX_ITERATIONS = 5
MAX_CONSECUTIVE_FAILURES = 2

THINK_SYSTEM_PROMPT = """Tu es un agent de recherche autonome (pattern ReAct) qui construit le profil
d'un prospect (l'organisation qui a publié un appel d'offres) en utilisant un outil de recherche web.

Retourne UNIQUEMENT un JSON avec ce format exact:
{
  "thought": "raisonnement court",
  "action": "web_search" ou "finish",
  "action_input": "requête de recherche précise, incluant si possible le nom de l'organisation" ou "",
  "final_profile": {
      "company_name": string,
      "sector": string,
      "estimated_revenue": string,
      "key_partners": [string],
      "past_projects": [string],
      "research_notes": string
  }
}

Règles importantes:
- Base tes requêtes sur le nom de l'organisation fourni dans le contexte, pas seulement sur un secteur générique.
- Ne finis JAMAIS dès la première itération si aucune recherche n'a encore été faite.
- Si une recherche échoue ou ne donne rien, reformule avec des mots-clés différents (nom + "budget", nom + "projets", nom + "partenaires").
- Passe à "finish" seulement quand tu as au moins 2 informations concrètes, ou après plusieurs échecs consécutifs.
- N'invente jamais un chiffre ou un partenaire non trouvé: utilise "unknown" plutôt que d'inventer.

Exemple de bonne première action (organisation connue, aucune recherche encore faite):
{
  "thought": "Je ne sais rien sur cette organisation, je commence par une recherche générale.",
  "action": "web_search",
  "action_input": "Ministère de la Santé Tunisie projets numériques budget 2025",
  "final_profile": {}
}

Ne retourne jamais autre chose que ce JSON.
"""


class AgentState(TypedDict):
    organization_hint: str
    tender_summary: str
    tender_sector: str
    history: str
    iteration: int
    consecutive_failures: int
    final_profile: Optional[dict]
    finished: bool
    next_query: str


def _default_profile(sector: str, reason: str) -> dict:
    return {
        "company_name": "unknown",
        "sector": sector,
        "estimated_revenue": "unknown",
        "key_partners": [],
        "past_projects": [],
        "research_notes": f"Profil incomplet: {reason}",
    }


def think_node(state: AgentState) -> AgentState:
    user_prompt = f"""
Organisation cible: {state['organization_hint']}
Secteur: {state['tender_sector']}
Résumé de l'appel d'offres: {state['tender_summary']}

Historique des recherches effectuées:
{state['history'] if state['history'] else "(aucune recherche encore effectuée)"}

Itération: {state['iteration']} / {MAX_ITERATIONS}
Échecs consécutifs: {state['consecutive_failures']}
"""
    try:
        decision = chat_json(THINK_SYSTEM_PROMPT, user_prompt)
    except ValueError:
        state["final_profile"] = _default_profile(
            state["tender_sector"], "le modèle n'a pas produit de décision exploitable"
        )
        state["finished"] = True
        return state

    state["iteration"] += 1

    wants_to_finish = decision.get("action") == "finish"
    must_stop = (
        state["iteration"] >= MAX_ITERATIONS
        or state["consecutive_failures"] >= MAX_CONSECUTIVE_FAILURES
    )

    if wants_to_finish and state["iteration"] == 1 and not must_stop:
        state["next_query"] = f"{state['organization_hint']} secteur activité chiffre d'affaires partenaires"
        state["finished"] = False
        return state

    if wants_to_finish or must_stop:
        profile = decision.get("final_profile") or {}
        for key, value in _default_profile(
            state["tender_sector"], "recherche arrêtée avant complétude totale"
        ).items():
            profile.setdefault(key, value)
        state["final_profile"] = profile
        state["finished"] = True
    else:
        query = (decision.get("action_input") or "").strip() or f"{state['organization_hint']} {state['tender_sector']}"
        state["next_query"] = query
        state["finished"] = False

    return state


def act_node(state: AgentState) -> AgentState:
    query = state["next_query"]
    result = call_mcp_tool("web_search", {"query": query})

    failed = (
        result.startswith("MCP_TOOL_ERROR")
        or result.lower().startswith("erreur")
        or "aucun résultat" in result.lower()
    )

    if failed:
        state["consecutive_failures"] += 1
        state["history"] += f"\n\n[Recherche SANS RESULTAT: {query}]\n{result}"
    else:
        state["consecutive_failures"] = 0
        state["history"] += f"\n\n[Recherche: {query}]\n{result}"

    return state


def should_continue(state: AgentState) -> str:
    return "end" if state["finished"] else "act"


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("think", think_node)
    graph.add_node("act", act_node)
    graph.set_entry_point("think")
    graph.add_conditional_edges("think", should_continue, {"act": "act", "end": END})
    graph.add_edge("act", "think")
    return graph.compile()


_compiled_graph = build_graph()


def run_market_intelligence_agent(organization_hint: str, tender_summary: str, tender_sector: str) -> dict:
    initial_state: AgentState = {
        "organization_hint": organization_hint or "unknown",
        "tender_summary": tender_summary,
        "tender_sector": tender_sector,
        "history": "",
        "iteration": 0,
        "consecutive_failures": 0,
        "final_profile": None,
        "finished": False,
        "next_query": "",
    }
    final_state = _compiled_graph.invoke(initial_state)
    return {"profile": final_state["final_profile"], "trace": final_state["history"]}