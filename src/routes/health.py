"""Health check route."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from src.models import HealthStatus

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthStatus)
async def health_check(request: Request) -> HealthStatus:
    """Check the health of all agent components."""
    components: dict[str, str] = {}

    # Check LLM provider
    try:
        llm_provider = request.app.state.llm_provider
        components["llm_provider"] = f"ready ({llm_provider.get_provider_name()})"
        components["model"] = llm_provider.get_model_name()
    except Exception as e:
        components["llm_provider"] = f"error: {str(e)}"

    # Check tool registry
    try:
        tool_registry = request.app.state.tool_registry
        tools = tool_registry.get_all_tools()
        components["tools"] = f"{len(tools)} tools available"
        components["tool_names"] = ", ".join(t.name for t in tools)
    except Exception as e:
        components["tools"] = f"error: {str(e)}"

    # Check conversation store
    try:
        store = request.app.state.conversation_store
        convs = await store.list_conversations()
        components["conversation_store"] = f"ready ({len(convs)} conversations)"
    except Exception as e:
        components["conversation_store"] = f"error: {str(e)}"

    # Check agent graph
    try:
        _ = request.app.state.agent_graph
        components["agent_graph"] = "compiled"
    except Exception as e:
        components["agent_graph"] = f"error: {str(e)}"

    status = "healthy" if "error" not in str(components.values()) else "degraded"

    return HealthStatus(
        status=status,
        version="0.1.0",
        provider=request.app.state.llm_provider.get_provider_name(),
        components=components,
    )
