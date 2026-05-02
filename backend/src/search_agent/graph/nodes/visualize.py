from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langchain_core.messages import AIMessage
from langgraph.types import RunnableConfig

from search_agent.graph.nodes.base import configurable
from search_agent.graph.nodes.plan_or_route import trace_step
from search_agent.graph.state import SearchAgentState

if TYPE_CHECKING:
    from search_agent.services.visualization_service import VisualizationService


async def visualize_node(state: SearchAgentState, config: RunnableConfig) -> dict[str, Any]:
    if not state.get("need_chart"):
        return {}
    c = configurable(config)
    viz: VisualizationService = c["visualization"]
    b64 = viz.chart_from_state_context(state)
    if not b64:
        b64 = viz.chart_result_counts(["note"], [1])
    return {
        "chart_png_base64": b64,
        "run_trace": [
            trace_step(
                "visualize",
                "Generated chart",
                "matplotlib PNG for response",
            )
        ],
        "messages": [AIMessage(content="[chart] Generated matplotlib figure.")],
    }
