"""
Graph state is a LangGraph `TypedDict` in `search_agent.graph.state`.

Pydantic models in `search_agent.models.api` are used for HTTP boundaries only.
Run trace items in graph state are plain dicts compatible with `TraceStep.to_state_dict`.
"""
