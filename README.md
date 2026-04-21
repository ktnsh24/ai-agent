# AI Agent — Tool-Using AI with LangGraph

> **Phase 3** of the AI Engineering Portfolio — An AI agent built with LangGraph that uses tools (web search, calculator, database queries), maintains conversation history, and streams responses via SSE.

**Port:** 8200 · **Language:** Python 3.12 · **Framework:** FastAPI + LangGraph + LangChain

---

## Quick Links

### Getting Started

| Document | Description |
|---|---|
| [Getting Started](docs/setup-and-tooling/getting-started.md) | Prerequisites, installation, first run — step by step |
| [Debugging Guide](docs/setup-and-tooling/debugging-guide.md) | VS Code + PyCharm debugger setup, breakpoints |

### Architecture & Design

| Document | Description |
|---|---|
| [Architecture Overview](docs/architecture-and-design/architecture.md) | System design, agent graph, tool flow |

### AI Engineering

| Document | Description |
|---|---|
| [LangGraph Deep Dive](docs/ai-engineering/langgraph-deep-dive.md) | Agent graph, state management, conditional edges |
| [Tool Use Deep Dive](docs/ai-engineering/tool-use-deep-dive.md) | Function calling, tool registry, safe execution |
| [Conversation Persistence Deep Dive](docs/ai-engineering/conversation-persistence-deep-dive.md) | SQLite + async SQLAlchemy, history management |
| [Cost Analysis](docs/ai-engineering/cost-analysis.md) | Token multiplier effect, tool costs, alternatives |

### Hands-On Labs

| Document | Description |
|---|---|
| [Phase 1 — Foundation](docs/hands-on-labs/hands-on-labs-phase-1.md) | Setup, first chat, tool invocation |
| [Phase 2 — Advanced](docs/hands-on-labs/hands-on-labs-phase-2.md) | Multi-turn conversations, streaming, tool chaining |

### Testing & Reference

| Document | Description |
|---|---|
| [Testing Strategy & Inventory](docs/ai-engineering/testing.md) | All tests — unit, integration, E2E |
| [Pydantic Models](docs/reference/pydantic-models.md) | Every model explained — every field, why it exists |

---

## What Does This Project Do?

A **tool-using AI agent** that implements the ReAct (Reason + Act) pattern:

1. **You send a message** → the agent analyses it and decides what to do
2. **Needs a tool?** → invokes web search, calculator, or database query
3. **Observes the result** → reasons about it, may invoke more tools
4. **Returns a final answer** → with tool call history and metadata

```
User Message → Agent Graph (LangGraph)
                    │
                    ├─ 1. Think (LLM call)
                    │       "I need to calculate this..."
                    │
                    ├─ 2. Act (Tool call)
                    │       calculator("sqrt(144)") → "12"
                    │
                    ├─ 3. Observe (Tool result)
                    │       "The result is 12"
                    │
                    └─ 4. Respond
                            "The square root of 144 is 12."
```

| Provider | LLM | Cost |
|---|---|---|
| **AWS** | Bedrock (Claude 3.5 Sonnet) | ~$0.003/1K tokens |
| **Azure** | Azure OpenAI (GPT-4o) | ~$0.0025/1K tokens |
| **Local** | Ollama (llama3.2) | **$0** |

---

## Advanced Features

| Feature | What it does | Pattern |
|---|---|---|
| **ReAct agent loop** | Think → Decide → Act → Observe → Repeat | LangGraph StateGraph |
| **Tool use** | Web search (Tavily), calculator (safe eval), database queries (SQLite) | `BaseToolProvider` ABC + registry |
| **Conversation persistence** | SQLite storage with async SQLAlchemy | `BaseConversationStore` ABC |
| **SSE streaming** | Real-time response streaming via Server-Sent Events | `EventSourceResponse` |
| **MCP client** | Placeholder for Phase 4 MCP server integration | `MCPToolProvider` |
| **Safe evaluation** | Calculator uses AST parsing — no `eval()` | Whitelist of operators + functions |
| **SQL safety** | Database queries are read-only (SELECT only) | Blocked keyword detection |

---

## Project Structure

```
ai-agent/
├── .github/workflows/          # CI/CD pipelines
├── docs/                       # Documentation (organised by topic)
│   ├── ai-engineering/         #   LangGraph, tool use, conversation persistence, testing
│   ├── architecture-and-design/#   Architecture overview
│   ├── hands-on-labs/          #   2 phases of guided labs
│   ├── reference/              #   Pydantic models reference
│   └── setup-and-tooling/      #   Getting started, debugging
├── infra/                      # Terraform (AWS + Azure)
├── src/                        # Application source code
│   ├── config.py               #   Pydantic Settings (all env vars)
│   ├── main.py                 #   FastAPI factory + lifespan manager
│   ├── models.py               #   Request/response Pydantic models
│   ├── agent/                  #   Core agent logic
│   │   ├── graph.py            #   LangGraph StateGraph (ReAct loop)
│   │   └── conversation.py     #   Conversation persistence (SQLite / in-memory)
│   ├── llm/                    #   LLM providers
│   │   └── provider.py         #   Bedrock, Azure OpenAI, Ollama (strategy pattern)
│   ├── tools/                  #   Agent tools
│   │   ├── registry.py         #   Tool registry + provider aggregation
│   │   ├── calculator.py       #   Safe math expression evaluator (AST-based)
│   │   ├── database_query.py   #   Read-only SQL against sample SQLite DB
│   │   └── web_search.py       #   Tavily search (or mock fallback)
│   └── routes/                 #   API endpoints
│       ├── health.py           #   GET /health — component status
│       ├── chat.py             #   POST /v1/chat + POST /v1/chat/stream (SSE)
│       ├── tools.py            #   GET /v1/tools — list available tools
│       └── conversations.py    #   GET/DELETE /v1/conversations
├── scripts/                    # Lab runner + utilities
│   ├── run_all_labs.py         #   8 automated lab experiments
│   ├── run_cloud_labs.sh       #   One-command cloud deploy → run → destroy
│   └── lab_results/            #   Lab output (local/, aws/, azure/)
├── tests/                      # Unit + integration tests
│   ├── test_api.py             #   Health, tools, chat, conversations (11 tests)
│   ├── test_calculator.py      #   Safe eval: arithmetic, functions, edge cases (17 tests)
│   ├── test_conversation.py    #   CRUD, persistence, message retrieval (8 tests)
│   └── test_database_query.py  #   SQL safety, sample data, queries (13 tests)
├── data/                       # Sample SQLite database (auto-created)
├── pyproject.toml              # Poetry dependencies
├── Dockerfile                  # Container image
├── docker-compose.yml          # Full stack: app + sample DB
└── .env.example                # Environment variable template
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/chat` | Send a message to the agent (sync response) |
| `POST` | `/v1/chat/stream` | Stream agent response via SSE |
| `GET` | `/v1/tools` | List available tools |
| `GET` | `/v1/conversations` | List all conversations |
| `GET` | `/v1/conversations/{id}` | Get conversation with all messages |
| `DELETE` | `/v1/conversations/{id}` | Delete a conversation |
| `GET` | `/health` | Health check with component status |

---

## Tools

| Tool | Description | API Key Required |
|---|---|---|
| **web_search** | Search the web via Tavily (or mock) | Optional (`TAVILY_API_KEY`) |
| **calculator** | Safe math: +, -, *, /, sqrt(), sin(), log(), pi | No |
| **database_query** | Read-only SQL on products + orders tables | No |

---

## Quick Start

```bash
# 1. Install Ollama and pull model
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2

# 2. Install dependencies
cd repos/ai-agent && poetry install

# 3. Configure
cp .env.example .env

# 4. Run
poetry run start
# → http://localhost:8200/docs
```

```bash
# Chat with the agent
curl -X POST http://localhost:8200/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the square root of 144?"}'

# List available tools
curl http://localhost:8200/v1/tools
```

### Run on AWS or Azure

```bash
# Deploy + run all labs + destroy (automated)
./scripts/run_cloud_labs.sh --provider aws --email you@example.com

# Custom budget limit (default €5)
./scripts/run_cloud_labs.sh --provider aws --email you@example.com --cost-limit 15
```

Results saved to `scripts/lab_results/<aws|azure>/`.

See [Getting Started](docs/setup-and-tooling/getting-started.md) for the full step-by-step guide.

---

## Tech Stack

| Layer | AWS | Azure | Local |
|---|---|---|---|
| **Language** | Python 3.12 | Python 3.12 | Python 3.12 |
| **Agent Framework** | LangGraph + LangChain | LangGraph + LangChain | LangGraph + LangChain |
| **LLM** | Bedrock (Claude 3.5 Sonnet) | Azure OpenAI (GPT-4o) | Ollama (llama3.2) |
| **Conversation Store** | DynamoDB (planned) | Cosmos DB (planned) | SQLite / in-memory |
| **Web Search** | Tavily API | Tavily API | Mock (no API key needed) |
| **Container** | ECS Fargate | Container Apps | Docker |

---

## Design Patterns

| Pattern | Where | Why |
|---|---|---|
| **ReAct Loop** | `AgentGraph._build_graph()` | Think → Act → Observe → Repeat |
| **Strategy (ABC + Factory)** | `BaseLLMProvider`, `BaseToolProvider`, `BaseConversationStore` | Swap providers without code changes |
| **Factory Method** | `create_llm_provider()`, `create_tool_registry()`, `create_conversation_store()` | Single entry point |
| **State Graph** | LangGraph `StateGraph` | Typed state flows through agent nodes |
| **Tool Registry** | `ToolRegistry` aggregates multiple `BaseToolProvider`s | Extensible tool system |
| **Safe Evaluation** | AST-based calculator | No `eval()` — whitelist only |

---

## Documentation Structure

```
docs/
├── ai-engineering/                               ← Deep-dives + testing
│   ├── langgraph-deep-dive.md                   ← Agent graph, state, edges
│   ├── tool-use-deep-dive.md                    ← Function calling, safe execution
│   ├── conversation-persistence-deep-dive.md    ← SQLite + async SQLAlchemy
│   ├── testing.md                               ← Test strategy & inventory
│   └── cost-analysis.md                         ← Token costs, alternatives
├── architecture-and-design/                     ← System design
│   └── architecture.md                          ← Architecture overview
├── hands-on-labs/                               ← Guided experiments
│   ├── hands-on-labs-phase-1.md                 ← Foundation: setup, chat, tools
│   └── hands-on-labs-phase-2.md                 ← Advanced: multi-turn, streaming
├── reference/                                   ← Models reference
│   └── pydantic-models.md                      ← Every model explained
└── setup-and-tooling/                           ← Getting started
    ├── getting-started.md                       ← Full setup guide
    └── debugging-guide.md                       ← Debugger setup
```

**Recommended reading order:**

1. [Architecture](docs/architecture-and-design/architecture.md) — how the agent graph works
2. [Getting Started](docs/setup-and-tooling/getting-started.md) — run it locally
3. [LangGraph Deep Dive](docs/ai-engineering/langgraph-deep-dive.md) — the ReAct loop explained
4. [Tool Use Deep Dive](docs/ai-engineering/tool-use-deep-dive.md) — function calling patterns

---

## Certification Relevance

| Agent Concept | AWS Service | Exam Relevance |
|---|---|---|
| Agent graph / state machine | Step Functions | SAA-C03: workflow orchestration |
| Tool invocation | Lambda | SAA-C03: serverless compute |
| Conversation persistence | DynamoDB | SAA-C03: NoSQL design |
| SSE streaming | API Gateway WebSocket | SAA-C03: real-time protocols |
| SQL safety | IAM least privilege | SAA-C03: security principles |
| Container orchestration | ECS Fargate | SAA-C03: compute services |

---

**Phase:** Phase 3 (out of 5) · **Portfolio:** [Portfolio Overview](../../README.md)
