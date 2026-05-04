from __future__ import annotations

import operator
from typing import Annotated, Any, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class SearchAgentState(TypedDict, total=False):
    """LangGraph state: merge semantics via Annotated reducers."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    run_trace: Annotated[list[dict[str, Any]], operator.add]

    query: str
    need_web: bool
    need_wiki: bool
    need_chart: bool
    need_alpha_vantage: bool
    alpha_vantage_keywords: str
    plan_reason: str
    wiki_query: str

    web_results: list[dict[str, Any]]
    page_extractions: list[dict[str, Any]]
    wiki_title: str
    wiki_summary: str
    wiki_url: str

    chart_png_base64: str
    alpha_vantage_chart: dict[str, Any]
    final_answer: str
    citations: list[str]

    verify_route: str
    verify_retry_count: int
    verify_quality_score: int
    verify_reason: str
    verify_feedback: str
    pending_web_query: str
    pending_wiki_query: str
