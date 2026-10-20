from typing import TypedDict, Optional, Callable
from langgraph.graph import StateGraph, END

from app.services.ollama_client import chat_json
from app.agents.mcp_client import call_mcp_tool


class ReactState(TypedDict):
    context_prompt: str
    system_prompt: str
    history: str
    iteration: int
    consecutive_failures: int
    max_iterations: int
    max_consecutive_failures: int
    final_output: Optional[dict]
    finished: bool
    next_query: str
    seed_query: str


def _build_think_node(default_output_fn: Callable[[str], dict]):
    def think_node(state: ReactState) -> ReactState:
        user_prompt = f"""
{state['context_prompt']}

Historique des recherches effectuées:
{state['history'] if state['history'] else "(aucune recherche encore effectuée)"}

Itération: {state['iteration']} / {state['max_iterations']}
Échecs consécutifs: {state['consecutive_failures']}
"""
        try:
            decision = chat_json(state["system_prompt"], user_prompt)
        except ValueError:
            state["final_output"] = default_output_fn("le modèle n'a pas produit de décision exploitable")
            state["finished"] = True
            return state

        state["iteration"] += 1
        wants_to_finish = decision.get("action") == "finish"
        must_stop = (
            state["iteration"] >= state["max_iterations"]
            or state["consecutive_failures"] >= state["max_consecutive_failures"]
        )

        if wants_to_finish and state["iteration"] == 1 and not must_stop:
            # edge case: le modèle veut conclure sans avoir rien cherché -> on force une 1ère recherche
            state["next_query"] = state["seed_query"]
            state["finished"] = False
            return state

        if wants_to_finish or must_stop:
            output = decision.get("final_output") or {}
            default = default_output_fn("recherche arrêtée avant complétude totale")
            for key, value in default.items():
                output.setdefault(key, value)
            state["final_output"] = output
            state["finished"] = True
        else:
            query = (decision.get("action_input") or "").strip() or state["seed_query"]
            state["next_query"] = query
            state["finished"] = False

        return state
    return think_node


def act_node(state: ReactState) -> ReactState:
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


def should_continue(state: ReactState) -> str:
    return "end" if state["finished"] else "act"


def run_react_agent(
    system_prompt: str,
    context_prompt: str,
    default_output_fn: Callable[[str], dict],
    seed_query: str,
    max_iterations: int = 5,
    max_consecutive_failures: int = 2,
) -> dict:
    graph = StateGraph(ReactState)
    graph.add_node("think", _build_think_node(default_output_fn))
    graph.add_node("act", act_node)
    graph.set_entry_point("think")
    graph.add_conditional_edges("think", should_continue, {"act": "act", "end": END})
    graph.add_edge("act", "think")
    compiled = graph.compile()

    initial_state: ReactState = {
        "context_prompt": context_prompt,
        "system_prompt": system_prompt,
        "history": "",
        "iteration": 0,
        "consecutive_failures": 0,
        "max_iterations": max_iterations,
        "max_consecutive_failures": max_consecutive_failures,
        "final_output": None,
        "finished": False,
        "next_query": "",
        "seed_query": seed_query,
    }
    final_state = compiled.invoke(initial_state)
    return {"output": final_state["final_output"], "trace": final_state["history"]}