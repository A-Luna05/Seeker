from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langchain_core.messages import AIMessage
from langgraph.types import RunnableConfig

from search_agent.graph.nodes.base import configurable
from search_agent.graph.nodes.plan_or_route import trace_step
from search_agent.graph.state import SearchAgentState

if TYPE_CHECKING:
    from search_agent.services.page_fetch_service import PageFetchService


def _unique_urls(web: list[dict[str, Any]], *, cap: int) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for w in web:
        if not isinstance(w, dict):
            continue
        u = str(w.get("url") or w.get("href") or "").strip()
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(u)
        if len(out) >= cap:
            break
    return out


async def fetch_pages_node(state: SearchAgentState, config: RunnableConfig) -> dict[str, Any]:
    c = configurable(config)
    svc: PageFetchService = c["page_fetch"]
    web = state.get("web_results") or []
    urls = _unique_urls(web, cap=5)
    if not urls:
        return {
            "page_extractions": [],
            "run_trace": [
                trace_step(
                    "fetch_pages",
                    "Parallel page fetch",
                    "skipped (no web URLs)",
                )
            ],
        }

    extractions = await svc.fetch_many(urls)
    ok_n = sum(1 for e in extractions if e.get("ok"))
    preview = "; ".join(e["url"].split("/")[-1][:40] for e in extractions if e.get("ok"))[:300]
    return {
        "page_extractions": extractions,
        "run_trace": [
            trace_step(
                "fetch_pages",
                "Parallel page fetch",
                f"{ok_n}/{len(urls)} pages extracted. {preview or '(none)'}",
            )
        ],
        "messages": [AIMessage(content=f"[fetch] {ok_n}/{len(urls)} pages text extracted.")],
    }
