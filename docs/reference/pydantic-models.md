# Pydantic Models Reference — AI Agent

> All request/response models used in the AI Agent API

---

## Enums

### `CloudProvider`

```python
class CloudProvider(str, Enum):
    AWS = "aws"
    AZURE = "azure"
    LOCAL = "local"
```

### `AgentStatus`

```python
class AgentStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    MAX_ITERATIONS = "max_iterations"
```

### `MessageRole`

```python
class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"
```

---

## Request Models

### `AgentRequest`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `message` | `str` | required | User message |
| `conversation_id` | `str \| None` | `None` | Continue existing conversation |
| `stream` | `bool` | `False` | Enable SSE streaming |
| `tools_enabled` | `bool` | `True` | Allow agent to use tools |

### Example

```json
{
  "message": "Calculate 2^10 + sqrt(144)",
  "conversation_id": "abc-123",
  "stream": false,
  "tools_enabled": true
}
```

---

## Response Models

### `AgentResponse`

| Field | Type | Description |
|-------|------|-------------|
| `message` | `str` | Agent's response text |
| `conversation_id` | `str` | Conversation identifier |
| `tool_calls` | `list[ToolCall]` | Tools used during execution |
| `iterations` | `int` | Number of ReAct loop iterations |
| `status` | `AgentStatus` | Execution outcome |
| `model` | `str` | Model used (e.g., `llama3.2`) |
| `latency_ms` | `float` | Total processing time |
| `tokens_used` | `int \| None` | Estimated token count |

### `ToolCall`

| Field | Type | Description |
|-------|------|-------------|
| `tool` | `str` | Tool name (e.g., `calculator`) |
| `input` | `str` | Input passed to the tool |
| `output` | `str` | Tool's response |

### Example

```json
{
  "message": "2^10 + √144 = 1024 + 12 = 1036",
  "conversation_id": "abc-123",
  "tool_calls": [
    {
      "tool": "calculator",
      "input": "2**10 + 144**0.5",
      "output": "1036.0"
    }
  ],
  "iterations": 2,
  "status": "success",
  "model": "llama3.2",
  "latency_ms": 1250.5,
  "tokens_used": 340
}
```

---

## Streaming Models

### `StreamEvent`

| Field | Type | Description |
|-------|------|-------------|
| `type` | `str` | Event type: `thinking`, `tool_call`, `token`, `done`, `error` |
| `content` | `str \| None` | Text content (for thinking/token events) |
| `tool` | `str \| None` | Tool name (for tool_call events) |
| `input` | `str \| None` | Tool input (for tool_call events) |
| `message` | `str \| None` | Full message (for done events) |
| `error` | `str \| None` | Error detail (for error events) |

---

## Conversation Models

### `ConversationSummary`

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Conversation UUID |
| `title` | `str` | Auto-generated from first message |
| `message_count` | `int` | Total messages |
| `created_at` | `datetime` | Creation timestamp |
| `updated_at` | `datetime` | Last update timestamp |

### `ConversationDetail`

Extends `ConversationSummary` with:

| Field | Type | Description |
|-------|------|-------------|
| `messages` | `list[ChatMessage]` | Full message history |

### `ChatMessage`

| Field | Type | Description |
|-------|------|-------------|
| `role` | `MessageRole` | user, assistant, system, or tool |
| `content` | `str` | Message content |
| `timestamp` | `datetime` | When the message was sent |

---

## Tool Models

### `ToolInfo`

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Tool identifier |
| `description` | `str` | What the tool does |
| `provider` | `str` | Source: `builtin` or `mcp` |

### `ToolListResponse`

| Field | Type | Description |
|-------|------|-------------|
| `tools` | `list[ToolInfo]` | Available tools |
| `count` | `int` | Total tool count |

---

## Health Model

### `HealthStatus`

| Field | Type | Description |
|-------|------|-------------|
| `status` | `str` | `healthy` or `unhealthy` |
| `version` | `str` | Application version |
| `provider` | `str` | Current cloud provider |
| `components` | `dict` | Component-level status |

---

## Error Model

### `AgentError`

| Field | Type | Description |
|-------|------|-------------|
| `error` | `str` | Error type |
| `detail` | `str` | Human-readable description |
| `status_code` | `int` | HTTP status code |

---

**Related:** [Architecture](../architecture-and-design/architecture.md) · [API Contract](../architecture-and-design/api-contract.md)
