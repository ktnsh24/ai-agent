"""Tools route — list available agent tools."""

from __future__ import annotations

from fastapi import APIRouter, Request

from src.models import ToolListResponse

router = APIRouter()


@router.get("/tools", response_model=ToolListResponse)
async def list_tools(request: Request) -> ToolListResponse:
    """List all available tools the agent can use."""
    tool_registry = request.app.state.tool_registry
    return ToolListResponse(tools=tool_registry.get_all_tool_info())
