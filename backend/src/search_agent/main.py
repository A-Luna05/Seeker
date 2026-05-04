from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from search_agent.api.routes_agent import router as agent_router
from search_agent.config import get_settings
from search_agent.graph.builder import build_compiled_graph
from search_agent.llm.litellm_client import LiteLLMClient
from search_agent.persistence.checkpointer import CheckpointerResources, create_postgres_checkpointer
from search_agent.services.alpha_vantage_service import AlphaVantageService
from search_agent.services.duckduckgo_service import DuckDuckGoService
from search_agent.services.page_fetch_service import PageFetchService
from search_agent.services.pdf_report_service import PdfReportService
from search_agent.services.visualization_service import VisualizationService
from search_agent.services.wikipedia_service import WikipediaService


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.openai_api_key:
        import os

        os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)

    app.state.llm = LiteLLMClient(settings.litellm_default_model)
    app.state.duckduckgo = DuckDuckGoService(
        brave_search_api_key=settings.brave_search_api_key or None,
    )
    app.state.page_fetch = PageFetchService()
    app.state.wikipedia = WikipediaService()
    app.state.alpha_vantage = AlphaVantageService(settings.alphavantage_api_key or None)
    app.state.visualization = VisualizationService()
    app.state.pdf = PdfReportService()

    cp_resources: CheckpointerResources | None = None
    checkpointer: Any
    if settings.database_url.strip():
        cp_resources = await create_postgres_checkpointer(settings.database_url.strip())
        checkpointer = cp_resources.checkpointer
    else:
        from langgraph.checkpoint.memory import MemorySaver

        checkpointer = MemorySaver()

    app.state.checkpointer = checkpointer
    app.state.cp_resources = cp_resources
    app.state.graph = build_compiled_graph(checkpointer)

    yield

    if cp_resources is not None:
        await cp_resources.aclose()


def create_app() -> FastAPI:
    app = FastAPI(title="Search Agent", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(agent_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
