from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langchain_core.messages import AIMessage
from langgraph.types import RunnableConfig

from search_agent.graph.nodes.base import configurable
from search_agent.graph.nodes.plan_or_route import trace_step
from search_agent.graph.state import SearchAgentState

if TYPE_CHECKING:
    from search_agent.services.wikipedia_service import WikipediaService


async def wiki_context_node(state: SearchAgentState, config: RunnableConfig) -> dict[str, Any]:
    pending_lookup = (state.get("pending_wiki_query") or "").strip()
    if not state.get("need_wiki") and not pending_lookup:
        return {}
    c = configurable(config)
    svc: WikipediaService = c["wikipedia"]
    raw = state.get("query") or ""
    focused = (state.get("wiki_query") or "").strip()
    if pending_lookup:
        lookup = pending_lookup
    else:
        lookup = focused if focused else raw
    res = await svc.summarize(lookup, sentences=5)
    base: dict[str, Any] = {}
    if pending_lookup:
        base["pending_wiki_query"] = ""
        base["need_wiki"] = True
    if not res:
        prior = (state.get("wiki_summary") or "").strip()
        if prior:
            # Later passes (e.g. after verify → web_search) hit Wikipedia again; transient failures
            # or rate limits must not clear a good summary from an earlier step.
            return {
                **base,
                "run_trace": [
                    trace_step(
                        "wiki_context",
                        "Wikipedia",
                        f"Lookup {lookup[:80]!r} returned no page; keeping prior summary",
                    )
                ],
                "messages": [AIMessage(content="[wiki] Kept previous Wikipedia summary.")],
            }
        return {
            **base,
            "wiki_title": "",
            "wiki_summary": "",
            "wiki_url": "",
            "run_trace": [
                trace_step(
                    "wiki_context",
                    "Wikipedia",
                    f"No summary found (lookup: {lookup[:120]})",
                )
            ],
            "messages": [AIMessage(content="[wiki] No summary found.")],
        }
    return {
        **base,
        "wiki_title": res.title,
        "wiki_summary": res.summary,
        "wiki_url": res.url,
        "run_trace": [
            trace_step(
                "wiki_context",
                "Wikipedia summary",
                f"{res.title[:200]} (lookup: {lookup[:120]})",
            )
        ],
        "messages": [AIMessage(content=f"[wiki] {res.title}")],
    }
