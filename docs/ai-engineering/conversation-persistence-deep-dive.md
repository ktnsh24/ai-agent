# Conversation Persistence Deep Dive — AI Agent

> **What:** Storing and retrieving chat history for multi-turn conversations
>
> **Why:** Without persistence, every request starts fresh — the agent has no memory
>
> **File:** `src/agent/conversation.py`

---

## Why Conversation Persistence Matters

| Without Persistence | With Persistence |
|--------------------|-----------------|
| "What's my name?" → "I don't know" | "What's my name?" → "Your name is Alex" |
| Each request is independent | Multi-turn dialogue |
| No context accumulation | Agent learns from conversation |

## Strategy Pattern

```python
class BaseConversationStore(ABC):
    async def create_conversation(self, title: str) -> str: ...
    async def add_message(self, conv_id: str, role: str, content: str) -> None: ...
    async def get_messages(self, conv_id: str) -> list[BaseMessage]: ...
    async def list_conversations(self) -> list[ConversationSummary]: ...
    async def delete_conversation(self, conv_id: str) -> bool: ...
```

| Implementation | Backend | Use Case |
|---------------|---------|----------|
| `SQLiteConversationStore` | SQLite + aiosqlite | Default — file-based, survives restarts |
| `InMemoryConversationStore` | Python dict | Testing — no file I/O |

## Database Schema

```sql
CREATE TABLE conversations (
    id VARCHAR(32) PRIMARY KEY,
    title VARCHAR(200),
    created_at DATETIME,
    updated_at DATETIME
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id VARCHAR(32) REFERENCES conversations(id),
    role VARCHAR(20),     -- system, user, assistant, tool
    content TEXT,
    tool_name VARCHAR(100),
    tool_call_id VARCHAR(100),
    timestamp DATETIME
);
```

## Message Flow

```
1. User sends: {"message": "Hi", "conversation_id": null}
2. Store creates new conversation → conversation_id = "abc123"
3. Store saves: {role: "user", content: "Hi"}
4. Agent runs with empty history
5. Store saves: {role: "assistant", content: "Hello! How can I help?"}
6. Returns: {conversation_id: "abc123", message: "Hello!..."}

Next request:
1. User sends: {"message": "What's AI?", "conversation_id": "abc123"}
2. Store loads history: [user: "Hi", assistant: "Hello!..."]
3. Agent runs with history + new message
4. Agent has context from prior turns
```

## Why SQLite?

| Storage | Pros | Cons |
|---------|------|------|
| **SQLite** | Zero config, file-based, SQL queries | Single-writer |
| PostgreSQL | Multi-writer, production scale | Requires running server |
| Redis | Fast, TTL-based | Not ideal for relational data |
| JSON files | Simple | No concurrent access |

SQLite is perfect for a single-instance agent. For multi-instance, upgrade to PostgreSQL.

## Cross-References

| Topic | Document |
|-------|----------|
| Agent architecture | [Architecture](../architecture-and-design/architecture.md) |
| LangGraph state | [LangGraph Deep Dive](../ai-engineering/langgraph-deep-dive.md) |
| API endpoints | [Getting Started](../setup-and-tooling/getting-started.md) |
