# Testing Strategy & Inventory — AI Agent

> How the AI Agent is tested — unit tests for tools and conversation store, integration tests for the full agent pipeline, and the patterns that make it all work without Ollama or external APIs.

**Related:** [Architecture](../architecture-and-design/architecture.md) · [Getting Started](../setup-and-tooling/getting-started.md)

---

## Test Pyramid

```
        ╱ ╲           E2E (manual via curl / Swagger UI)
       ╱   ╲          Verify full stack with real Ollama
      ╱─────╲
     ╱       ╲        Integration (24 tests)
    ╱         ╲       Full pipeline: route → agent graph → conversation store
   ╱───────────╲
  ╱             ╲     Unit (49 tests)
 ╱               ╲    Calculator, database queries, conversation CRUD, API endpoints
╱─────────────────╲
```

---

## Running Tests

```bash
# All tests
poetry run pytest tests/ -v

# Integration tests only
poetry run pytest tests/test_integration.py -v

# Specific test class
poetry run pytest tests/test_integration.py::TestChatPipeline -v

# With coverage
poetry run pytest tests/ --cov=src --cov-report=term-missing
```

---

## Test Inventory

### Unit Tests (4 files, ~49 tests)

| File | Tests | What it covers |
|---|---|---|
| `test_api.py` | 11 | Health, tools, chat, conversations — basic endpoint tests |
| `test_calculator.py` | 17 | Safe eval: arithmetic, functions, edge cases, security |
| `test_conversation.py` | 8 | InMemoryConversationStore: CRUD, messages, persistence |
| `test_database_query.py` | 13 | SQL safety, sample data, blocked keywords, read-only |

### Integration Tests (1 file, 24 tests)

| File | Tests | What it covers |
|---|---|---|
| `test_integration.py` | 24 | Chat pipeline, conversation flow, tool calls, error handling |

**Total: 5 files, ~73 tests**

---

## Test Patterns

### 1. Direct app.state Assignment

Components are mocked directly on `app.state`, bypassing the lifespan manager:

```python
app = create_app()
app.state.llm_provider = mock_llm
app.state.agent_graph = mock_agent
app.state.conversation_store = InMemoryConversationStore()
```

### 2. Real In-Memory Store

The `InMemoryConversationStore` is used without mocking — it's a real implementation that works without SQLite:

```python
@pytest.fixture
def conversation_store():
    return InMemoryConversationStore()
```

### 3. Shared Fixtures (conftest.py)

`tests/conftest.py` provides:
- `mock_llm_provider` — MagicMock with provider/model name
- `mock_tool_registry` — MagicMock with 3 default tools
- `mock_agent_graph` — AsyncMock with default AgentResponse
- `conversation_store` — Real InMemoryConversationStore
- `app` / `client` — Fully wired test app + client

---

## Known Limitations

| Limitation | Why | Mitigation |
|---|---|---|
| LangGraph is mocked | Can't run real agent graph in CI | Mock returns realistic AgentResponse |
| SSE streaming not tested | Requires async client | Manual E2E testing with curl |
| No Tavily API tests | Requires API key | Web search has mock fallback |
| No SQLite integration tests | Would need async setup | InMemoryConversationStore covers the interface |

---

## DE Parallel — What This Looks Like at Scale

| Layer | What | Tools |
|---|---|---|
| **Agent tests** | Test LangGraph state transitions with real graph | LangGraph test utilities |
| **Tool tests** | Test each tool with real external services | Testcontainers for databases |
| **SSE tests** | Async SSE client testing | httpx-sse, pytest-asyncio |
| **Conversation tests** | Real SQLite with async migrations | aiosqlite + alembic |
| **Performance tests** | Agent latency under load | Locust with concurrent conversations |
