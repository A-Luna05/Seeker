from __future__ import annotations

from typing import Any

from langgraph.graph import START, StateGraph

from search_agent.graph.nodes.alpha_vantage import alpha_vantage_node
from search_agent.graph.nodes.fetch_pages import fetch_pages_node
from search_agent.graph.nodes.plan_or_route import plan_node
from search_agent.graph.nodes.synthesize import synthesize_node
from search_agent.graph.nodes.verify import verify_node
from search_agent.graph.nodes.visualize import visualize_node
from search_agent.graph.nodes.web_search import web_search_node
from search_agent.graph.nodes.wiki_context import wiki_context_node
from search_agent.graph.routing import VERIFY_EDGE_MAP, route_after_verify
from search_agent.graph.state import SearchAgentState


def build_compiled_graph(checkpointer: Any) -> Any:
    g = StateGraph(SearchAgentState)
    g.add_node("plan", plan_node)
    g.add_node("alpha_vantage", alpha_vantage_node)
    g.add_node("web_search", web_search_node)
    g.add_node("fetch_pages", fetch_pages_node)
    g.add_node("wiki_context", wiki_context_node)
    g.add_node("visualize", visualize_node)
    g.add_node("synthesize", synthesize_node)
    g.add_node("verify", verify_node)
    g.add_edge(START, "plan")
    g.add_edge("plan", "alpha_vantage")
    g.add_edge("alpha_vantage", "web_search")
    g.add_edge("web_search", "fetch_pages")
    g.add_edge("fetch_pages", "wiki_context")
    g.add_edge("wiki_context", "visualize")
    g.add_edge("visualize", "synthesize")
    g.add_edge("synthesize", "verify")
    g.add_conditional_edges("verify", route_after_verify, VERIFY_EDGE_MAP)
    return g.compile(checkpointer=checkpointer)
