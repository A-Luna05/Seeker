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


def _urls_from_web_and_wiki(web: list[dict[str, Any]], wiki_src: str) -> set[str]:
    allowed: set[str] = set()
    for w in web:
        u = w.get("url") or w.get("href")
        if isinstance(u, str) and u.strip():
            allowed.add(u.strip())
    if wiki_src.strip():
        allowed.add(wiki_src.strip())
    return allowed


def _citation_allowed(citation: str, allowed: set[str]) -> bool:
    c = citation.strip()
    if not c.startswith("http"):
        return False
    c_norm = c.rstrip("/")
    for a in allowed:
        a_norm = a.rstrip("/")
        if c_norm == a_norm:
            return True
        if c_norm.startswith(a_norm + "/") or a_norm.startswith(c_norm + "/"):
            return True
        if c_norm in a_norm or a_norm in c_norm:
            return True
    return False


def _filter_citations_to_context(
    citations: list[str],
    web: list[dict[str, Any]],
    wiki_src: str,
) -> list[str]:
    allowed = _urls_from_web_and_wiki(web, wiki_src)
    if not allowed:
        return []
    return [c for c in citations if _citation_allowed(c, allowed)]


async def synthesize_node(state: SearchAgentState, config: RunnableConfig) -> dict[str, Any]:
    c = configurable(config)
    llm: LiteLLMClient = c["llm"]
    model_raw = c.get("model")
    model: str | None = str(model_raw) if model_raw is not None else None
    query = state.get("query") or ""

    web = state.get("web_results") or []
    web_bullets = "\n".join(
        f"- {w.get('title','')}: {w.get('snippet','')[:300]} ({w.get('url','')})"
        for w in web[:8]
    )
    extractions = state.get("page_extractions") or []
    fetch_parts: list[str] = []
    budget = 24_000
    for e in extractions:
        if not isinstance(e, dict) or not e.get("ok"):
            continue
        u = str(e.get("url") or "").strip()
        tx = str(e.get("text") or "").strip()
        if not u or not tx:
            continue
        chunk = f"URL: {u}\n{tx[:5000]}"
        if len(chunk) > budget:
            chunk = chunk[:budget] + "\n…"
        fetch_parts.append(chunk)
        budget -= len(chunk)
        if budget < 500:
            break
    fetch_block = "\n\n---\n".join(fetch_parts) if fetch_parts else "(none)"

    wiki = (state.get("wiki_summary") or "").strip()
    wiki_src = (state.get("wiki_url") or "").strip()
    wiki_q = (state.get("wiki_query") or "").strip()
    revision = (state.get("verify_feedback") or "").strip()

    sys = SystemMessage(
        content=(
            "You synthesize a helpful answer using ONLY the provided context. "
            "Respond ONLY with JSON: {\"answer\": string, \"citations\": string[]} "
            "Rules: citations MUST be URLs that appear verbatim in the Web results block "
            "(the parenthesized URL at the end of each line) or exactly the Wikipedia Source URL. "
            "If Web results are (none), you MUST NOT invent or guess external URLs—use an empty "
            "citations array or only the Wikipedia Source URL if you used Wikipedia. "
            "When \"Fetched page excerpts\" are present, prefer concrete facts, numbers, and table rows "
            "from those excerpts over vague generalities. "
            "Be concise and accurate."
        )
    )
    ctx_parts = [
        f"User query:\n{query}\n",
        f"Wikipedia lookup phrase (planner): {wiki_q or '(use raw query)'}\n",
        f"Web results:\n{web_bullets or '(none)'}\n",
        f"Fetched page excerpts (HTML text/tables; use for specifics):\n{fetch_block}\n",
        f"Wikipedia:\n{wiki or '(none)'}\nSource: {wiki_src or '(none)'}\n",
    ]
    if revision:
        ctx_parts.append(f"\nRevision note (address in an improved answer):\n{revision}\n")
    ctx = HumanMessage(content="".join(ctx_parts))
    resp = await llm.complete(
        [sys, ctx],
        model=model,
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    data = _extract_json_object(str(resp.content))
    answer = str(data.get("answer", "")).strip()
    citations = data.get("citations") or []
    if not isinstance(citations, list):
        citations = []
    citations = [str(c).strip() for c in citations if str(c).strip()][:20]
    citations = _filter_citations_to_context(citations, web, wiki_src)

    return {
        "final_answer": answer,
        "citations": citations,
        "run_trace": [
            trace_step(
                "synthesize",
                "Final answer",
                answer[:400],
            )
        ],
        "messages": [AIMessage(content=answer)],
    }
