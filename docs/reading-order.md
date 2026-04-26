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
| 3 | Getting Started | Install dependencies, configure settings, run locally | Load up the courier — install the gear, set the config, send it on the first test run |
| 4 | Environment Config | All settings flags: `cloud_provider`, tool enable flags, MCP flag, conversation store URL | The dashboard switches — which city, which tools, which filing cabinet |

---

## Level 3 — Understand the Core (AI Pipeline)

Deep dives into the core components, in data-flow order.

| # | Document | What you'll learn | 🚚 Courier |
|---|----------|-------------------|-----------|
| 5 | LangGraph Deep Dive | StateGraph topology, ReAct loop, `add_messages` annotation, `AgentState` | The courier's think-act rulebook — how she loops, when she stops, what she carries between trips |
| 6 | Tool Use Deep Dive | How tools are registered, bound to the LLM, and executed via `ToolNode` | The van's tool bay — how each tool is bolted on, what the LLM sees, how results come back |
| 7 | LLM Providers Deep Dive | Bedrock (Claude 3.5 Sonnet v2), Azure OpenAI, Ollama — how each is constructed and called | Three courier fleets — same job description (abstract interface), different employer |
| 8 | Conversation Store Deep Dive | SQLiteConversationStore vs InMemoryConversationStore — schema, message reconstruction, `ToolMessage` gap | The filing cabinet — locked (SQLite) vs clipboard (in-memory), what each can and cannot remember |

---

## Level 4 — Understand the API

Deep dives into each route, in importance order.

| # | Document | What you'll learn | ⭐ |
|---|----------|-------------------|----|
| 9 | ⭐ [Chat Endpoint](architecture-and-design/api-routes/chat-endpoint-explained.md) | **Canonical walkthrough** — full ReAct loop, Factory Method + Strategy, conversation store, tool calls, response construction | ★★★★★ |
| 10 | [Chat Stream Endpoint](architecture-and-design/api-routes/chat-stream-endpoint-explained.md) | SSE event sequence, simulated token streaming, generator store-write bug | ★★★★☆ |
| 11 | [Conversations Endpoint](architecture-and-design/api-routes/conversations-endpoint-explained.md) | List/get/delete conversation history, SQLite vs in-memory fidelity difference, `ToolMessage` gap | ★★★☆☆ |
| 12 | [Tools Endpoint](architecture-and-design/api-routes/tools-endpoint-explained.md) | Tool registry snapshot, web_search (Tavily/mock), calculator (AST sandbox), database_query (keyword guard + bypass), MCP dead wiring | ★★★☆☆ |
| 13 | [Health Endpoint](architecture-and-design/api-routes/health-endpoint-explained.md) | Shallow string-check health, `"degraded"`-aware status, what "healthy" does and does not guarantee | ★☆☆☆☆ |
