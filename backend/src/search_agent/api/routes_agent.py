from __future__ import annotations

import base64
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from langchain_core.messages import HumanMessage

from search_agent.api.checkpoint_serialize import serialize_checkpoint_values
from search_agent.models.api import (
    Artifact,
    CheckpointListResponse,
    CheckpointStateResponse,
    CheckpointSummary,
    RunAgentRequest,
    RunAgentResponse,
)
from search_agent.services.pdf_report_service import PdfReportService

router = APIRouter(prefix="/api", tags=["agent"])


@router.post("/runs", response_model=RunAgentResponse)
async def run_agent(body: RunAgentRequest, request: Request) -> RunAgentResponse:
    graph = request.app.state.graph
    thread_id = body.thread_id or str(uuid4())

    init: dict[str, Any] = {
        "query": body.query.strip(),
        "messages": [HumanMessage(content=body.query.strip())],
        "run_trace": [],
    }
    cfg = {
        "configurable": {
            "thread_id": thread_id,
            "llm": request.app.state.llm,
            "duckduckgo": request.app.state.duckduckgo,
            "page_fetch": request.app.state.page_fetch,
            "wikipedia": request.app.state.wikipedia,
            "visualization": request.app.state.visualization,
            "model": body.model,
        }
    }
    try:
        result = await graph.ainvoke(init, config=cfg)
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e)) from e

    answer = str(result.get("final_answer", "")).strip()
    citations = list(result.get("citations") or [])
    trace = list(result.get("run_trace") or [])
    artifacts: list[Artifact] = []
    chart_b64 = result.get("chart_png_base64")
    if chart_b64:
        artifacts.append(
            Artifact(
                mime_type="image/png",
                label="Chart",
                data_base64=str(chart_b64),
            )
        )

    pdf_b64: str | None = None
    if body.include_pdf:
        pdf_svc: PdfReportService = request.app.state.pdf
        pdf_bytes = pdf_svc.build_from_run_state(result)
        pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")

    plan_info = {
        "need_web": result.get("need_web"),
        "need_wiki": result.get("need_wiki"),
        "need_chart": result.get("need_chart"),
        "reason": result.get("plan_reason", ""),
        "wiki_query": result.get("wiki_query", ""),
        "verify_route": result.get("verify_route"),
        "verify_quality_score": result.get("verify_quality_score"),
        "verify_retries": result.get("verify_retry_count"),
        "verify_reason": result.get("verify_reason", ""),
    }

    return RunAgentResponse(
        thread_id=thread_id,
        answer=answer,
        citations=citations,
        artifacts=artifacts,
        run_trace=trace,
        pdf_base64=pdf_b64,
        plan=plan_info,
    )


@router.get("/threads/{thread_id}/checkpoints", response_model=CheckpointListResponse)
async def list_thread_checkpoints(thread_id: str, request: Request) -> CheckpointListResponse:
    checkpointer = request.app.state.checkpointer
    config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}
    summaries: list[CheckpointSummary] = []
    try:
        async for cp in checkpointer.alist(config):
            cid: str | None = None
            chk = cp.checkpoint
            if isinstance(chk, dict):
                raw_id = chk.get("id") or chk.get("checkpoint_id")
                if raw_id is not None:
                    cid = str(raw_id)
            meta_raw = cp.metadata
            meta: dict[str, Any] = dict(meta_raw) if isinstance(meta_raw, dict) else {}
            summaries.append(
                CheckpointSummary(
                    checkpoint_id=cid,
                    thread_id=thread_id,
                    metadata=meta,
                )
            )
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e)) from e
    return CheckpointListResponse(thread_id=thread_id, checkpoints=summaries)


def _parent_checkpoint_id(parent_config: Any) -> str | None:
    if not parent_config or not isinstance(parent_config, dict):
        return None
    conf = parent_config.get("configurable")
    if not isinstance(conf, dict):
        return None
    cid = conf.get("checkpoint_id")
    return str(cid) if cid else None


def _snapshot_to_response(
    thread_id: str,
    *,
    checkpoint_id: str | None,
    snapshot: Any,
) -> CheckpointStateResponse:
    meta = snapshot.metadata
    meta_dict = dict(meta) if isinstance(meta, dict) else {}
    values_raw = snapshot.values
    values_dict = values_raw if isinstance(values_raw, dict) else {"_state": values_raw}
    cid = checkpoint_id
    if cid is None and snapshot.config:
        cconf = snapshot.config.get("configurable") if isinstance(snapshot.config, dict) else None
        if isinstance(cconf, dict) and cconf.get("checkpoint_id"):
            cid = str(cconf["checkpoint_id"])
    next_nodes = list(snapshot.next) if snapshot.next else []
    return CheckpointStateResponse(
        thread_id=thread_id,
        checkpoint_id=cid,
        created_at=snapshot.created_at,
        parent_checkpoint_id=_parent_checkpoint_id(snapshot.parent_config),
        metadata=meta_dict,
        next=next_nodes,
        values=serialize_checkpoint_values(values_dict),
    )


@router.get("/threads/{thread_id}/state", response_model=CheckpointStateResponse)
async def get_thread_latest_state(thread_id: str, request: Request) -> CheckpointStateResponse:
    """Return merged graph state at the latest checkpoint for this thread."""
    graph = request.app.state.graph
    cfg: dict[str, Any] = {"configurable": {"thread_id": thread_id}}
    try:
        snap = await graph.aget_state(cfg)
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e)) from e
    cconf = snap.config.get("configurable") if isinstance(snap.config, dict) else None
    cid = str(cconf["checkpoint_id"]) if isinstance(cconf, dict) and cconf.get("checkpoint_id") else None
    return _snapshot_to_response(thread_id, checkpoint_id=cid, snapshot=snap)


@router.get(
    "/threads/{thread_id}/checkpoints/{checkpoint_id}/state",
    response_model=CheckpointStateResponse,
)
async def get_checkpoint_state(
    thread_id: str,
    checkpoint_id: str,
    request: Request,
) -> CheckpointStateResponse:
    """Return full graph channel values stored at a specific checkpoint id."""
    graph = request.app.state.graph
    cfg: dict[str, Any] = {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id,
        }
    }
    try:
        snap = await graph.aget_state(cfg)
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e)) from e
    return _snapshot_to_response(thread_id, checkpoint_id=checkpoint_id, snapshot=snap)
