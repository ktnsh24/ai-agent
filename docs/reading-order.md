# 📚 Documentation Reading Order

> A guided path through the ai-agent documentation. Start at Level 1 and work your way down.

---

## 🚀 Want the whole architecture in one read?

If you only have time for **one document** to understand how the agent actually works end-to-end — every step, every branch, every quirk, in plain English with worked examples and the courier analogy — read this:

➡️ **[Chat Endpoint → Architecture Walkthrough](architecture-and-design/api-routes/chat-endpoint-explained.md#architecture-walkthrough-start-here)**

It covers the full agent pipeline: startup assembly (Factory Method + Strategy Pattern), LangGraph ReAct loop (two nodes, conditional routing, `add_messages` annotation), conversation lookup/creation, tool calls, store writes, and response construction — plus the honest list of rough edges a code review would surface.

> #### 📌 Note
> Every endpoint doc in [Level 4](#level-4--understand-the-api) opens with its own **Architecture Walkthrough (Start Here)** section at the top — same style, same courier analogy. Once you've read the chat walkthrough, the others are quick add-ons covering only what's different for that endpoint.

---

## Level 1 — Start Here (The Big Picture)

Read these first to understand what this project is and how it works.

| # | Document | What you'll learn | 🚚 Courier |
|---|----------|-------------------|-----------|
| 1 | [README.md](../README.md) | Project overview, features, tech stack, quick start | The depot notice board — what the courier does, what tools it carries, how to get it started |
| 2 | [Architecture Overview](architecture-and-design/architecture.md) | System diagram, component relationships, data flow | The delivery route map — all roads, stops, and handoffs from question to answer |

---

## Level 2 — Setup & Run It

Get the project running on your machine.

| # | Document | What you'll learn | 🚚 Courier |
|---|----------|-------------------|-----------|
| 3 | [Getting Started](setup-and-tooling/getting-started.md) | Install dependencies, configure settings, run locally | Load up the courier — install the gear, set the config, send it on the first test run |
| 4 | [Docker Compose Guide](setup-and-tooling/docker-compose-guide.md) | Run the full stack in Docker; local Ollama wiring, SQLite volume | The containerised depot — one command spins up the whole operation |
| 5 | [Debugging Guide](setup-and-tooling/debugging-guide.md) | Common errors, log reading, tool failure diagnosis | The depot maintenance manual — what to check when a courier doesn't come back |

---

## Level 3 — Understand the Core (AI Pipeline)

Deep dives into the core components, in data-flow order.

| # | Document | What you'll learn | 🚚 Courier |
|---|----------|-------------------|-----------|
| 6 | [LangGraph Deep Dive](ai-engineering/langgraph-deep-dive.md) | StateGraph topology, ReAct loop, `add_messages` annotation, `AgentState`, iteration guard | The courier's think-act rulebook — how she loops, when she stops, what she carries between trips |
| 7 | [Tool Use Deep Dive](ai-engineering/tool-use-deep-dive.md) | How tools are registered, bound to the LLM, and executed via `ToolNode`; AST calculator; Tavily vs mock | The van's tool bay — how each tool is bolted on, what the LLM sees, how results come back |
| 8 | [Conversation Persistence Deep Dive](ai-engineering/conversation-persistence-deep-dive.md) | SQLiteConversationStore vs InMemoryConversationStore — schema, message reconstruction, `ToolMessage` gap | The filing cabinet — locked (SQLite) vs clipboard (in-memory), what each can and cannot remember |
| 9 | [Cost Analysis](ai-engineering/cost-analysis.md) | Token estimation heuristic (`chars // 4`), per-provider cost considerations | The expense ledger — rough estimates, honest caveats |
| 10 | [Testing](ai-engineering/testing.md) | Test structure, what is and is not covered | The quality inspector — what the depot checks before opening |

---

## Level 4 — Understand the API

Deep dives into each route, in importance order. See also the [API Routes Index](architecture-and-design/api-routes-explained.md) for a one-page summary.

| # | Document | What you'll learn | ⭐ |
|---|----------|-------------------|----|
| 11 | ⭐ [Chat Endpoint](architecture-and-design/api-routes/chat-endpoint-explained.md) | **Canonical walkthrough** — full ReAct loop, Factory Method + Strategy, conversation store, tool calls, response construction | ★★★★★ |
| 12 | [Chat Stream Endpoint](architecture-and-design/api-routes/chat-stream-endpoint-explained.md) | SSE event sequence, simulated token streaming, generator store-write bug | ★★★★☆ |
| 13 | [Conversations Endpoint](architecture-and-design/api-routes/conversations-endpoint-explained.md) | List/get/delete conversation history, SQLite vs in-memory fidelity difference, `ToolMessage` gap | ★★★☆☆ |
| 14 | [Tools Endpoint](architecture-and-design/api-routes/tools-endpoint-explained.md) | Tool registry snapshot, web_search (Tavily/mock), calculator (AST sandbox), database_query (keyword guard + bypass), MCP dead wiring | ★★★☆☆ |
| 15 | [Health Endpoint](architecture-and-design/api-routes/health-endpoint-explained.md) | Shallow string-check health, `"degraded"`-aware status, what "healthy" does and does not guarantee | ★☆☆☆☆ |

---

## Level 5 — Infrastructure & Operations

How the service is deployed, monitored, and maintained.

| # | Document | What you'll learn | 🚚 Courier |
|---|----------|-------------------|-----------|
| 16 | [CI/CD Explained](architecture-and-design/cicd-explained.md) | lint → test → docker CI pipeline; manual deploy-aws and deploy-azure workflows; ECR + ECS update flow | The depot quality gate — every parcel batch is checked before the van leaves |
| 17 | [Infra Explained](architecture-and-design/infra-explained.md) | VPC, ECS Fargate, ECR, CloudWatch log group, IAM roles, budget guard (5 EUR default) | The depot's physical address — which building, which truck bay, who holds the keys |
| 18 | [Terraform Guide](setup-and-tooling/terraform-guide.md) | How to init/plan/apply AWS and Azure infra; required variables; OIDC auth | The architect's instruction manual — how to build the depot from scratch |
| 19 | [Monitoring](reference/monitoring.md) | CloudWatch logs, health endpoint, what is and is not instrumented (no LangFuse, no Prometheus) | The depot logbook — what gets written down and what doesn't |

---

## Level 6 — Hands-On Labs

Work through practical labs to reinforce understanding.

| # | Document | What you'll learn |
|---|----------|-------------------|
| 20 | [How to Read the Labs](hands-on-labs/how-to-read-the-labs.md) | Lab structure, prerequisites (Python 3.12, Poetry, Ollama), how to run |
| 21 | [Phase 1 Labs](hands-on-labs/hands-on-labs-phase-1.md) | Core agent setup and first tool calls |
| 22 | [Phase 2 Labs](hands-on-labs/hands-on-labs-phase-2.md) | Conversation persistence and multi-turn reasoning |
| 23 | [Config Tuning Labs](hands-on-labs/hands-on-labs-config-tuning.md) | Adjusting `max_iterations`, switching providers, enabling/disabling tools |

---

## Level 7 — Reference

Quick-lookup reference material.

| # | Document | What you'll learn |
|---|----------|-------------------|
| 24 | [Pydantic Models](reference/pydantic-models.md) | All request/response schemas — field names, types, defaults, validation rules |
