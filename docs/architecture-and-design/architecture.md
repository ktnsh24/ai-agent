# Architecture Overview — AI Agent

> **Pattern:** LangGraph StateGraph with ReAct loop + Strategy Pattern for providers
> **Framework:** FastAPI + LangGraph + LangChain

---

## System Context

```
┌──────────────────────────────────────────────────────────────┐
│                        Client Apps                           │
│  (Browser, CLI, Multi-Agent System)                          │
└────────────────────────────┬─────────────────────────────────┘
                             │ HTTP / SSE
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                     AI Agent (:8200)                          │
│                                                              │
│  ┌────────────────────────────────────────────────────┐      │
│  │              LangGraph Agent Loop                   │      │
│  │  ┌─────────┐    ┌──────────┐    ┌──────────────┐  │      │
│  │  │  Think  │ →  │  Decide  │ →  │  Act (tools) │  │      │
│  │  │  (LLM)  │    │ (route)  │    │              │  │      │
│  │  └─────────┘    └──────────┘    └──────┬───────┘  │      │
│  │       ↑                                │          │      │
│  │       └──────── Observe ←──────────────┘          │      │
│  └────────────────────────────────────────────────────┘      │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Tool Registry │  │ Conversation │  │ LLM Provider     │   │
│  │ ┌──────────┐ │  │ Store (SQLite)│  │ (Bedrock/Azure/ │   │
│  │ │ Search   │ │  │              │  │  Ollama)         │   │
│  │ │ Calc     │ │  │              │  │                  │   │
│  │ │ DB Query │ │  │              │  │                  │   │
│  │ └──────────┘ │  └──────────────┘  └──────────────────┘   │
│  └──────────────┘                                            │
└──────────────────────────────────────────────────────────────┘
```

## LangGraph State Machine

```
START → [Agent Node] → Decision
                         │
                    ┌────┴────┐
                    │         │
              has tools?  no tools
                    │         │
                    ▼         ▼
              [Tool Node]    END
                    │
                    └→ [Agent Node] → Decision → ...
```

### State Definition

```python
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    iterations: int
    max_iterations: int
    tool_calls_made: list[ToolCall]
```

## Strategy Pattern

| Component | ABC | Implementations |
|-----------|-----|-----------------|
| LLM Provider | `BaseLLMProvider` | `BedrockProvider`, `AzureOpenAIProvider`, `OllamaProvider` |
| Tool Provider | `BaseToolProvider` | `BuiltinToolProvider`, `MCPToolProvider` |
| Conversation Store | `BaseConversationStore` | `SQLiteConversationStore`, `InMemoryConversationStore` |

## Cross-References

| Topic | Document |
|-------|----------|
| LangGraph details | [LangGraph Deep Dive](../ai-engineering/langgraph-deep-dive.md) |
| Tool system | [Tool Use Deep Dive](../ai-engineering/tool-use-deep-dive.md) |
| Persistence | [Conversation Persistence](../ai-engineering/conversation-persistence-deep-dive.md) |
| Setup | [Getting Started](../setup-and-tooling/getting-started.md) |
