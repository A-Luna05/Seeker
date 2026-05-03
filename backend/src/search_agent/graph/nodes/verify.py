from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.types import RunnableConfig

from search_agent.graph.nodes.base import configurable
from search_agent.graph.nodes.plan_or_route import trace_step
from search_agent.graph.state import SearchAgentState

if TYPE_CHECKING:
    from search_agent.llm.litellm_client import LiteLLMClient

MAX_VERIFY_LOOPS = 3


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return {}


def _web_summary(web: list[dict[str, Any]]) -> str:
    lines = []
    for w in web[:8]:
        lines.append(f"- {w.get('title', '')} ({w.get('url', '')})")
    return "\n".join(lines) if lines else "(none)"


def _fetch_summary(ext: list[dict[str, Any]]) -> str:
    if not ext:
        return "(none)"
    lines = []
    for e in ext[:5]:
        if not isinstance(e, dict):
            continue
        u = e.get("url") or ""
        mark = "ok" if e.get("ok") else (e.get("error") or "fail")
        lines.append(f"- {mark}: {u}")
        if e.get("ok") and e.get("text"):
            t = str(e["text"])[:400].replace("\n", " ")
            lines.append(f"  excerpt: {t}…")
    return "\n".join(lines) if lines else "(none)"


async def verify_node(state: SearchAgentState, config: RunnableConfig) -> dict[str, Any]:
    loops = int(state.get("verify_retry_count") or 0)
    if loops >= MAX_VERIFY_LOOPS:
        return {
            "verify_route": "end",
            "verify_feedback": "",
            "run_trace": [
                trace_step(
                    "verify",
                    "Quality check skipped",
                    f"cap reached ({MAX_VERIFY_LOOPS} retries); accepting draft",
                )
            ],
            "messages": [AIMessage(content="[verify] Max retries; accepting draft.")],
        }

    c = configurable(config)
    llm: LiteLLMClient = c["llm"]
    model_raw = c.get("model")
    model: str | None = str(model_raw) if model_raw is not None else None

    query = state.get("query") or ""
    answer = (state.get("final_answer") or "").strip()
    web = state.get("web_results") or []
    page_x = state.get("page_extractions") or []
    wiki = (state.get("wiki_summary") or "").strip()
    wiki_title = (state.get("wiki_title") or "").strip()
    need_web = bool(state.get("need_web"))
    need_wiki = bool(state.get("need_wiki"))

    sys = SystemMessage(
        content=(
            "You evaluate a draft answer for a search assistant. Output ONLY JSON:\n"
            '{ "quality_score": number from 1-10, '
            '"adequate": boolean (true only if the draft fully answers the user query with appropriate depth; '
            "false if anything important is missing, e.g. user asked for recent news but the draft has none), "
            '"route": one of "end", "more_web", "more_wiki", '
            '"reason": one short sentence, '
            '"refined_web_query": string (non-empty only if route is more_web; focused DuckDuckGo query), '
            '"refined_wiki_query": string (non-empty only if route is more_wiki; Wikipedia entity/title phrase), '
            '"feedback": string (if not adequate: what to fix; concise, for the writer) }\n'
            "Rules: If adequate is false because the query needs fresher or more specific facts, set route to more_web "
            "(or more_wiki for missing background), not end. Prefer \"end\" only when adequate is true or the gap "
            "cannot be fixed with another retrieval pass. Use more_web if sources/snippets are missing or stale. "
            "Use more_wiki if background from Wikipedia would help. "
            "Pick at most one retrieval route per turn. "
            "If the user/plan did not use web (need_web=false), still allow more_web if the draft clearly needs it. "
            "If need_wiki=false, still allow more_wiki if useful."
        )
    )
    human = HumanMessage(
        content=(
            f"User query:\n{query}\n\n"
            f"Planner: need_web={need_web}, need_wiki={need_wiki}\n\n"
            f"Web results (titles/urls):\n{_web_summary(web)}\n\n"
            f"Fetched pages (excerpts):\n{_fetch_summary(page_x)}\n\n"
            f"Wikipedia title: {wiki_title or '(none)'}\n"
            f"Wikipedia summary (trimmed):\n{wiki[:1200] if wiki else '(none)'}\n\n"
            f"Draft answer:\n{answer or '(empty)'}\n"
        )
    )
    resp = await llm.complete(
        [sys, human],
        model=model,
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    data = _extract_json_object(str(resp.content))
    adequate = bool(data.get("adequate", True))
    score = data.get("quality_score")
    try:
        qscore = int(score) if score is not None else 0
    except (TypeError, ValueError):
        qscore = 0
    qscore = max(0, min(10, qscore))
    reason = str(data.get("reason", "")).strip()[:400]
    route_raw = str(data.get("route", "end")).strip().lower()
    if route_raw not in ("end", "more_web", "more_wiki"):
        route_raw = "end"
    feedback = str(data.get("feedback", "")).strip()[:1500]

    refined_web = str(data.get("refined_web_query", "")).strip()[:300]
    refined_wiki = str(data.get("refined_wiki_query", "")).strip()[:200]

    if adequate:
        route = "end"
    elif route_raw == "more_web":
        route = "web_search"
    elif route_raw == "more_wiki":
        route = "wiki_context"
    else:
        route = "end"

    retry_delta = 1 if route in ("web_search", "wiki_context") else 0
    new_loops = loops + retry_delta

    pending_web = ""
    pending_wiki = ""
    out_feedback = ""
    if route == "web_search":
        pending_web = refined_web or query
        out_feedback = feedback or reason or "Refine using additional web results."
    elif route == "wiki_context":
        pending_wiki = refined_wiki or (state.get("wiki_query") or "").strip() or query
        out_feedback = feedback or reason or "Refine using Wikipedia context."

    detail = f"score={qscore}, adequate={adequate}, route={route}. {reason}"
    return {
        "verify_route": route,
        "verify_retry_count": new_loops,
        "verify_quality_score": qscore,
        "verify_reason": reason,
        "verify_feedback": out_feedback if route != "end" else "",
        "pending_web_query": pending_web if route == "web_search" else "",
        "pending_wiki_query": pending_wiki if route == "wiki_context" else "",
        "run_trace": [
            trace_step(
                "verify",
                "Draft quality check",
                detail[:500],
            )
        ],
        "messages": [AIMessage(content=f"[verify] {detail}")],
    }
