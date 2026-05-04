from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langchain_core.messages import AIMessage
from langgraph.types import RunnableConfig

from search_agent.graph.nodes.base import configurable
from search_agent.graph.nodes.plan_or_route import trace_step
from search_agent.graph.state import SearchAgentState

if TYPE_CHECKING:
    from search_agent.services.alpha_vantage_service import AlphaVantageService


async def alpha_vantage_node(state: SearchAgentState, config: RunnableConfig) -> dict[str, Any]:
    if not state.get("need_alpha_vantage"):
        return {}
    keywords = (state.get("alpha_vantage_keywords") or "").strip()
    if not keywords:
        return {
            "run_trace": [
                trace_step(
                    "alpha_vantage",
                    "Skipped market lookup",
                    "planner marked need_alpha_vantage but gave no keywords",
                )
            ],
        }

    c = configurable(config)
    svc: AlphaVantageService | None = c.get("alpha_vantage")  # type: ignore[assignment]
    if svc is None or not svc.configured:
        return {
            "run_trace": [
                trace_step(
                    "alpha_vantage",
                    "Skipped market lookup",
                    "ALPHAVANTAGE_API_KEY is not set",
                )
            ],
        }

    payload = await svc.lookup_equity_series(keywords)
    if not payload.get("ok"):
        err = str(payload.get("error") or "lookup failed")
        return {
            "run_trace": [
                trace_step(
                    "alpha_vantage",
                    "Market lookup failed",
                    f"{err} (keywords={keywords!r})",
                )
            ],
        }

    pts = payload.get("points") or []
    if not isinstance(pts, list) or not pts:
        return {
            "run_trace": [
                trace_step(
                    "alpha_vantage",
                    "No price series",
                    f"symbol={payload.get('symbol')!r}",
                )
            ],
        }

    sym = str(payload.get("symbol") or "")
    name = str(payload.get("name") or sym)
    chart = {
        "symbol": sym,
        "name": name,
        "interval": str(payload.get("interval") or "daily"),
        "points": pts,
    }
    last = pts[-1] if pts else {}
    first = pts[0] if pts else {}
    detail = (
        f"{name} ({sym}): {len(pts)} daily closes from {first.get('date')} "
        f"to {last.get('date')}, last close={last.get('close')}"
    )
    return {
        "alpha_vantage_chart": chart,
        "run_trace": [
            trace_step(
                "alpha_vantage",
                "Fetched market series",
                detail[:2000],
            )
        ],
        "messages": [AIMessage(content=f"[alpha_vantage] {sym} daily series ({len(pts)} pts).")],
    }
