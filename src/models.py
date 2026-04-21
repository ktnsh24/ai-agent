"""Pydantic models for AI Agent API requests and responses."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────────────────────


class AgentStatus(str, Enum):
    """Current agent execution status."""

    IDLE = "idle"
    THINKING = "thinking"
    TOOL_CALLING = "tool_calling"
    RESPONDING = "responding"
    ERROR = "error"
    COMPLETE = "complete"


class MessageRole(str, Enum):
    """Chat message roles."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


# ── Chat Messages ─────────────────────────────────────────────────────────


class ChatMessage(BaseModel):
    """A single message in a conversation."""

    role: MessageRole
    content: str
    tool_name: str | None = None
    tool_call_id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ToolCall(BaseModel):
    """A tool invocation by the agent."""

    id: str
    name: str
    arguments: dict
    result: str | None = None


# ── Requests ──────────────────────────────────────────────────────────────


class AgentRequest(BaseModel):
    """Request to the agent API."""

    message: str
    conversation_id: str | None = None
    stream: bool = False
    tools_enabled: bool = True
    max_iterations: int | None = None


# ── Responses ─────────────────────────────────────────────────────────────


class AgentResponse(BaseModel):
    """Response from the agent API."""

    conversation_id: str
    message: str
    tool_calls: list[ToolCall] = []
    iterations: int = 0
    status: AgentStatus = AgentStatus.COMPLETE
    model: str = ""
    provider: str = ""
    total_tokens: int = 0
    latency_ms: float = 0.0


class StreamEvent(BaseModel):
    """A single SSE event during streaming."""

    event: str  # "thinking", "tool_call", "token", "done", "error"
    data: str
    tool_call: ToolCall | None = None


# ── Conversations ─────────────────────────────────────────────────────────


class ConversationSummary(BaseModel):
    """Summary of a conversation."""

    id: str
    title: str
    message_count: int
    created_at: datetime
    updated_at: datetime


class ConversationDetail(BaseModel):
    """Full conversation with messages."""

    id: str
    title: str
    messages: list[ChatMessage]
    created_at: datetime
    updated_at: datetime


# ── Tools ─────────────────────────────────────────────────────────────────


class ToolInfo(BaseModel):
    """Information about an available tool."""

    name: str
    description: str
    parameters: dict
    enabled: bool = True


class ToolListResponse(BaseModel):
    """List of available tools."""

    tools: list[ToolInfo]


# ── Health ────────────────────────────────────────────────────────────────


class HealthStatus(BaseModel):
    """Health check response."""

    status: str
    version: str
    provider: str
    components: dict[str, str]


class AgentError(BaseModel):
    """Standard error response."""

    error: ErrorDetail


class ErrorDetail(BaseModel):
    """Error detail."""

    message: str
    type: str
    code: int
