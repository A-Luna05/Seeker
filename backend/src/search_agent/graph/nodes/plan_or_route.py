from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.types import RunnableConfig

from search_agent.graph.nodes.base import configurable
from search_agent.graph.state import SearchAgentState

if TYPE_CHECKING:
    from search_agent.llm.litellm_client import LiteLLMClient


def trace_step(
    node: str,
    title: str,
    detail: str = "",
) -> dict[str, Any]:
    return {
        "node": node,
        "title": title,
        "detail": detail[:2000],
        "ts": datetime.now(UTC).isoformat(),
    }


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


async def plan_node(state: SearchAgentState, config: RunnableConfig) -> dict[str, Any]:
    c = configurable(config)
    llm: LiteLLMClient = c["llm"]
    model = c.get("model")
    if model is not None:
        model = str(model)
    query = state.get("query") or ""
    sys = SystemMessage(
        content=(
            "You are a routing planner for a search assistant. "
            "Given the user query, output ONLY a compact JSON object with keys: "
            "need_web (boolean): use DuckDuckGo for fresh web results; "
            "need_wiki (boolean): use Wikipedia for stable background/overview; "
            "need_chart (boolean): true if the user asks for a chart, plot, graph, or numeric comparison; "
            "reason (string): one short sentence; "
            "wiki_query (string): if need_wiki is true, a SHORT Wikipedia article title or search phrase "
            "(proper noun / entity only, e.g. \"LeBron James\" not the full user question). "
            "If need_wiki is false, use an empty string for wiki_query. "
            "Important: need_web and need_wiki are independent—both may be true. "
            "For entity/fact/overview questions, set BOTH true unless the query clearly needs only one "
            "(e.g. pure breaking-news lookup → web only; narrowly scoped definition of one term with no "
            "recency angle → wiki only is acceptable). "
            'Example: {"need_web": true, "need_wiki": true, "need_chart": false, "reason": "...", '
            '"wiki_query": "LeBron James"}'
        )
    )
    human = HumanMessage(content=query)
    resp = await llm.complete(
        [sys, human],
        model=model,
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    data = _extract_json_object(str(resp.content))
    need_web = bool(data.get("need_web", True))
    need_wiki = bool(data.get("need_wiki", True))
    need_chart = bool(data.get("need_chart", False))
    reason = str(data.get("reason", ""))[:500]
    wiki_query = str(data.get("wiki_query", "")).strip()[:200]
    if not need_wiki:
        wiki_query = ""
    return {
        "need_web": need_web,
        "need_wiki": need_wiki,
        "need_chart": need_chart,
        "plan_reason": reason,
        "wiki_query": wiki_query,
        "run_trace": [
            trace_step(
                "plan",
                "Planned retrieval",
                f"web={need_web}, wiki={need_wiki}, chart={need_chart}. "
                f"wiki_query={wiki_query!r}. {reason}",
            )
        ],
        "messages": [AIMessage(content=f"[plan] {reason}")],
    }
