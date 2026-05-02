"""Conditional edge routing for the search agent graph."""

from __future__ import annotations

from langgraph.graph import END

from search_agent.graph.state import SearchAgentState


def route_after_verify(state: SearchAgentState) -> str:
    r = (state.get("verify_route") or "end").strip().lower()
    if r == "web_search":
        return "web_search"
    if r == "wiki_context":
        return "wiki_context"
    return "end"


VERIFY_EDGE_MAP = {
    "web_search": "web_search",
    "wiki_context": "wiki_context",
    "end": END,
}
