from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langchain_core.messages import AIMessage
from langgraph.types import RunnableConfig

from search_agent.graph.nodes.base import configurable
from search_agent.graph.nodes.plan_or_route import trace_step
from search_agent.graph.state import SearchAgentState

if TYPE_CHECKING:
    from search_agent.services.duckduckgo_service import DuckDuckGoService


def _merge_web_results(
    existing: list[dict[str, Any]],
    new_rows: list[dict[str, Any]],
    *,
    cap: int = 15,
) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in existing + new_rows:
        if not isinstance(row, dict):
            continue
        u = str(row.get("url") or row.get("href") or "").strip()
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(row)
        if len(out) >= cap:
            break
    return out


async def web_search_node(state: SearchAgentState, config: RunnableConfig) -> dict[str, Any]:
    pending = (state.get("pending_web_query") or "").strip()
    if not state.get("need_web") and not pending:
        return {}
    c = configurable(config)
    svc: DuckDuckGoService = c["duckduckgo"]
    base_q = state.get("query") or ""
    query = pending if pending else base_q
    hits = await svc.search(query, max_results=5)
    rows = [
        {"title": h.title, "url": h.url, "snippet": h.snippet}
        for h in hits
    ]
    prior_dicts = [p for p in (state.get("web_results") or []) if isinstance(p, dict)]
    if prior_dicts:
        merged = _merge_web_results(prior_dicts, rows)
    else:
        merged = rows
    preview = "; ".join(str(m.get("title", "")) for m in merged[:3])[:500]
    update: dict[str, Any] = {
        "web_results": merged,
        "pending_web_query": "",
        "run_trace": [
            trace_step(
                "web_search",
                "Web search results",
                (f"[q={query[:80]}] " if query != base_q else "") + (preview or "no hits"),
            )
        ],
        "messages": [AIMessage(content=f"[web] Retrieved {len(merged)} results.")],
    }
    if pending:
        update["need_web"] = True
    return update
