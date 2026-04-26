# Chat Endpoint — Deep Dive

> `POST /v1/chat` — Send a message to the AI agent; get a response with tool calls and conversation history.

> **Related docs:**
> - [Architecture Overview](../architecture.md) — system design
> - [Chat Stream Endpoint](chat-stream-endpoint-explained.md) — SSE streaming variant
> - [Conversations Endpoint](conversations-endpoint-explained.md) — history management
> - [Tools Endpoint](tools-endpoint-explained.md) — registered tool catalogue
> - [Health Endpoint](health-endpoint-explained.md) — liveness check

---

## Table of Contents

0. [Architecture Walkthrough (Start Here)](#architecture-walkthrough-start-here)
1. [Endpoint Summary](#endpoint-summary)
2. [Request and Response Shape](#request-and-response-shape)
3. [Step 1 — Conversation Lookup or Creation](#step-1--conversation-lookup-or-creation)
4. [Step 2 — Agent Graph Execution (ReAct Loop)](#step-2--agent-graph-execution-react-loop)
5. [Step 3 — Conversation Store Write](#step-3--conversation-store-write)
6. [Step 4 — Response Construction](#step-4--response-construction)
7. [Condition Matrix](#condition-matrix)
8. [Honest Health Check](#honest-health-check)
9. [TL;DR](#tldr)

---

## Architecture Walkthrough (Start Here)

> This walkthrough explains what really happens when a request hits `POST /v1/chat` — every design pattern, every strategy, every branch, and every known quirk. No code snippets, no file paths — but every strategy and trade-off that matters is called out explicitly.

---

### How the system is assembled at startup (before the first request arrives)

Before any request arrives, the application lifespan hook runs a **Factory Method** five times — once per component — and stores every result on `app.state`. This is **Factory Method + Strategy Pattern**: the factory reads a single config key (`settings.cloud_provider`) and constructs the correct concrete strategy for that environment; the rest of the application only ever talks to the abstract interface.

**Component 1 — LLM provider**

The factory reads `settings.cloud_provider` and instantiates one of three concrete strategies:

| `cloud_provider` value | Concrete class | Underlying library | Model |
|---|---|---|---|
| `aws` | `BedrockProvider` | `langchain_aws.ChatBedrock` | Claude 3.5 Sonnet v2 |
| `azure` | `AzureOpenAIProvider` | `langchain_openai.AzureChatOpenAI` | Deployment name from config |
| `local` | `OllamaProvider` | `langchain_ollama.ChatOllama` | Model name from config |
| Anything else | — | — | Raises `ValueError` — app fails to start |

An unknown provider raises immediately at startup, not on the first request. The application will not start at all with an unrecognised provider value.

**Component 2 — Tool registry**

`ToolRegistry` is always created. `BuiltinToolProvider` is always registered. `MCPToolProvider` is registered only if `settings.mcp_enabled=True` — but its `connect()` method body is a no-op stub that logs "not yet implemented (Phase 4)" and `get_tools()` always returns an empty list. MCP is dead wiring: the flag exists, the class exists, but zero MCP tools are ever available.

Three built-in tools are individually gated by config flags:

| Tool | Config flag | Behaviour when enabled |
|---|---|---|
| `web_search` | `tool_web_search_enabled` | Real Tavily search if `tavily_api_key` set; otherwise keyword-matched mock (3 keywords: "weather", "news", "default") |
| `calculator` | `tool_calculator_enabled` | Python AST safe-eval sandbox — no `eval()`, whitelisted operators and functions only |
| `database_query` | `tool_database_query_enabled` | Read-only SQLite against a bundled sample database with keyword guard |

**Component 3 — Conversation store**

The factory checks the configured database URL:

| Condition | Store created | Persistence |
|---|---|---|
| SQLite URL configured | `SQLiteConversationStore` (async SQLAlchemy) | Survives restarts; two tables: `conversations` and `messages` |
| No SQLite URL | `InMemoryConversationStore` (plain Python dict) | Lost on every restart |

**Component 4 — Agent graph**

`create_agent_graph(llm_provider, tool_registry, settings)` builds a LangGraph `StateGraph`. This is the core of the system — the full ReAct loop lives here. See Step 2 for the deep dive.

**Component 5 — CORS middleware**

Allows all origins with no restriction. There is no auth middleware, no rate-limiting middleware. Any caller with network access to the server can hit any endpoint without credentials.

If any factory call raises an exception, the application fails to start entirely. There is no graceful degradation at assembly time — it is all or nothing.

> **Courier version.** The depot is set up once before opening time. The manager reads the "which city are we in?" sign (`cloud_provider`) and hires the right courier fleet — AWS couriers know Bedrock, Azure couriers know Azure OpenAI, local couriers use Ollama. Three additional tools are bolted onto the courier van one by one, each controlled by its own switch on the dashboard. The parcel history archive is set up in either a proper filing cabinet (SQLite) or a clipboard on the wall (in-memory) — the clipboard is wiped every morning. Finally, the front door is left unlocked for anyone: no security guard, no sign-in sheet.

---

### The request pipeline — four steps in sequence

---

#### Step 1 — Conversation lookup or creation

The handler inspects the `conversation_id` field on the request body. There are two branches:

**Branch A — `conversation_id` provided:** The handler calls the conversation store's `get_messages()` method. If the store returns nothing (ID not found in SQLite or not in the in-memory dict), the handler immediately returns `404`. If found, the handler reconstructs the prior message list. The SQLite store reconstructs full LangChain message objects including `ToolMessage`; the in-memory store does not reconstruct `ToolMessage` objects — tool call history is silently dropped on replay from in-memory store.

**Branch B — No `conversation_id`:** The handler creates a new conversation record with the title set to the first 50 characters of the user's message. A new conversation ID is generated by the store and returned.

In both branches the user message is written to the store immediately — before the agent runs — so it is persisted even if the agent graph subsequently fails.

> **Courier version.** The clerk at the front desk checks whether the customer has an existing parcel tracking number. If yes, she pulls the full delivery history from the filing cabinet — if the cabinet has no record of that number, she turns the customer away with a "parcel not found" slip. If no tracking number, she opens a fresh file and labels it with the first few words of the customer's request. Either way, the customer's new note goes into the file immediately, before the courier even picks up the parcel — so the note is never lost even if the courier has a bad day.

---

#### Step 2 — Agent graph execution (ReAct loop)

This is the most technically dense part of the system. The handler calls `agent_graph.run(user_message, conversation_history, max_iterations)`.

**Graph topology**

The `StateGraph` has exactly two nodes and a loop:

- `agent` node — calls the LLM with the current message list
- `tools` node — executes tool calls via LangChain's `ToolNode`
- Entry point: `agent`
- Conditional edge from `agent` → either `tools` or `end` (decided by `should_continue()`)
- Fixed edge from `tools` → back to `agent` (creates the loop)

**`AgentState` flowing through the graph**

The state is a `TypedDict` with four fields:

| Field | Type | Behaviour |
|---|---|---|
| `messages` | `list[BaseMessage]` annotated with `add_messages` | Messages are **appended**, never replaced — each node update adds to the list, not overwrites it |
| `iterations` | int | Incremented by the `agent` node on every invocation |
| `max_iterations` | int | Set once at the start from `settings.agent_max_iterations`; never mutated |
| `tool_calls_made` | list | Always empty during graph execution; populated in post-processing after the graph finishes |

The `add_messages` annotation is the key design decision: it means each pass through the `agent` node appends the LLM's reply to the growing message list rather than replacing the list. The LLM therefore always receives the full conversation history on every iteration — this is how the ReAct loop maintains context.

**Initial state construction**

Before the graph runs, `AgentGraph.run()` builds the initial state in three steps:

1. Prepend a `SystemMessage` with a hardcoded system prompt describing the available tools
2. If `conversation_history` was passed (prior turns loaded from the store), extend the message list with those messages
3. Append a `HumanMessage` with the current user message

**`should_continue()` routing — two exit conditions**

After every `agent` node invocation, the conditional edge calls `should_continue()` on the current state:

| Condition checked | Outcome | Why |
|---|---|---|
| `state["iterations"] >= state["max_iterations"]` | Route to `"end"` | Safety limit — prevents infinite loops if the LLM keeps requesting tools |
| Last message is `AIMessage` with `tool_calls` present | Route to `"tools"` | LLM decided it needs a tool; execute it and loop back |
| Anything else (LLM produced a plain text answer) | Route to `"end"` | LLM signalled it is done |

The iteration limit is checked first. If the limit is hit, the graph exits even if the last message has pending tool calls — those tool calls are abandoned.

**Tool binding**

If tools are registered, the LLM is bound with `.bind_tools(tools)` at graph construction time. This injects the tool schemas (function definitions) into every LLM call. The LLM can then return an `AIMessage` with `tool_calls` populated. If no tools are registered, the LLM runs unbound — a plain chat completion with no function definitions.

**Token estimation**

After the graph finishes, `AgentGraph.run()` estimates the token count by dividing the total character count of all messages by 4. This is an explicit rough heuristic — not a real token count from the LLM response. The actual usage returned by the LLM API is not captured.

**`conversation_id` override**

The graph's `run()` generates a new `uuid4().hex[:16]` internally as its own `conversation_id`. The chat handler immediately overrides this with the actual conversation ID from the store. The `conversation_id` in the final response is always the store's ID, never the graph's internally generated one.

**Worked example — three-iteration tool-use trace**

To make the loop concrete, here is what the message list looks like across a question that requires two tool calls before the LLM answers:

| Iteration | Node | What runs | Message appended to list |
|---|---|---|---|
| 0 (initial) | — | `AgentGraph.run()` builds initial state | SystemMessage, (history), HumanMessage |
| 1 | `agent` | LLM receives full message list; decides it needs web_search | AIMessage with `tool_calls: [{web_search, "current weather London"}]` |
| 1 | `tools` | `ToolNode` executes web_search | ToolMessage with search result |
| 2 | `agent` | LLM receives updated message list; decides it needs calculator | AIMessage with `tool_calls: [{calculator, "15 + 273"}]` |
| 2 | `tools` | `ToolNode` executes calculator | ToolMessage with "288" |
| 3 | `agent` | LLM receives full message list including both tool results; produces final answer | AIMessage with plain text — no `tool_calls` |
| 3 | `should_continue()` | Last message is AIMessage with no tool_calls | Route to `"end"` |

Each row appends one message. By the time the LLM produces its final answer at iteration 3, the message list contains the system prompt, any prior history, the original human question, two AI-tool-call messages, two tool result messages, and finally the plain-text AIMessage.

> **Courier version.** The courier follows a think-act loop. She reads all the notes in her bag (system prompt + history + your question), decides what she needs, and either writes a delivery note (tool call) or writes the final answer. If she writes a delivery note, the tool team executes it and hands the result back into her bag. She reads everything again and decides again. A supervisor watches how many trips she has made — if she hits the trip limit, she is pulled off the floor regardless of whether she is done. Otherwise, as soon as she writes a plain letter with no delivery note, her shift ends and the letter goes to you.

---

#### Step 3 — Conversation store write

After the graph finishes, the handler writes the assistant's response to the store via `add_message(conversation_id, "assistant", response.message)`. The `updated_at` timestamp on the conversation record is updated via a raw SQL `UPDATE` statement on every `add_message()` call.

The user message was written before the graph ran (Step 1). The assistant message is written after. If the graph raises an exception, the user message is in the store but the assistant message is not — the conversation record will show the user's question with no reply.

> **Courier version.** When the courier returns with the final letter, the clerk files it in the customer's folder under "assistant reply". The customer's original note was filed at the start — so if the courier loses the parcel in transit, the customer's question is on record but no answer ever arrives.

---

#### Step 4 — Response construction

The handler assembles the `AgentResponse` from the graph's output:

- `message` — the plain text content of the final `AIMessage`
- `conversation_id` — overridden with the store's ID (see Step 2)
- `tool_calls_made` — extracted by `_extract_tool_calls()` which walks the finished message list post-graph; this field is **not** populated during graph execution
- `token_usage` — the rough character-divided-by-4 estimate
- `model` — the LLM provider's model name from config

> **Courier version.** The clerk compiles the delivery receipt: the letter text, the tracking number from the filing cabinet (not the courier's internal slip), a list of every delivery run the courier made (extracted from the trip log after she returns), and an estimated word count (characters divided by four — rough, but fast). The receipt goes back to the customer.

---

## Endpoint Summary

| Property | Value |
|---|---|
| Method | `POST` |
| Path | `/v1/chat` |
| Auth required | No |
| Rate limited | No |
| Streaming | No (use `/v1/chat/stream` for SSE) |
| Idempotent | No |

---

## Request and Response Shape

**Request body fields:**

| Field | Type | Required | Behaviour |
|---|---|---|---|
| `message` | string | Yes | The user's message sent to the agent |
| `conversation_id` | string | No | If provided, load prior history; 404 if not found |
| `max_iterations` | int | No | Override the default agent iteration limit |

**Response body fields:**

| Field | Type | Notes |
|---|---|---|
| `message` | string | Plain text content of the LLM's final response |
| `conversation_id` | string | The store's conversation ID — always the authoritative one |
| `tool_calls_made` | list | Tools called during this request, extracted post-graph |
| `token_usage` | int | Rough estimate: total chars ÷ 4 |
| `model` | string | LLM model name from config |

---

## Condition Matrix

| Scenario | What happens |
|---|---|
| `conversation_id` provided and found | Load history, prepend to graph state, continue |
| `conversation_id` provided and not found | `404` — no graph execution |
| No `conversation_id` | Create new conversation, assign new ID |
| LLM produces tool call | Route to `tools` node, execute, loop back to `agent` |
| LLM produces plain text reply | Route to `end`, return response |
| `max_iterations` reached | Route to `end` regardless of pending tool calls |
| Tool raises exception | Tool returns error string to LLM; LLM decides what to do next |
| `cloud_provider` unknown at startup | App fails to start — `ValueError` |
| `mcp_enabled=True` | `MCPToolProvider` registered but returns zero tools (stub) |
| No tools registered | LLM runs unbound — plain chat, no function definitions injected |
| SQLite URL configured | Persistent conversation store; survives restart |
| No SQLite URL | In-memory store; history lost on restart |

---

## 🩺 Honest Health Check

1. **No authentication on any endpoint.** Any caller with network access can read, write, and delete all conversations without credentials — add an API key or OAuth layer before any production exposure.

2. **MCP is dead wiring.** The `mcp_enabled` flag and `MCPToolProvider` class exist but `connect()` is a stub and `get_tools()` always returns empty — setting `mcp_enabled=True` has no effect until Phase 4 is implemented.

3. **Token estimation is a fiction.** Dividing character count by 4 is an explicit rough heuristic — actual LLM token usage is not retrieved from the API response, so `token_usage` in every response is an approximation that will be wrong for non-ASCII content.

4. **`tool_calls_made` is never populated during graph execution.** The field in `AgentState` is always empty while the graph runs; it is extracted post-hoc by scanning the finished message list — if the extraction logic misses a tool call pattern, it is silently absent from the response.

5. **In-memory store loses `ToolMessage` history.** When the in-memory store replays a conversation, it reconstructs only `HumanMessage`, `AIMessage`, and `SystemMessage` — `ToolMessage` objects are dropped, so the LLM in a continued conversation does not see prior tool results.

6. **User message is persisted before the graph runs.** If the agent graph raises an unhandled exception, the user's message is in the store with no corresponding assistant reply — a dangling record that will be included as history on the next request for this conversation.

7. **No rate limiting.** A single caller can hammer the LLM endpoint indefinitely; add middleware (e.g., `slowapi`) before any public exposure.

---

## TL;DR

- **Factory Method + Strategy Pattern** at startup: one config key (`cloud_provider`) selects the entire concrete LLM backend; the rest of the system talks to abstract interfaces.
- **ReAct loop via LangGraph `StateGraph`**: two nodes (`agent` + `tools`), a conditional router (`should_continue()`), and the `add_messages` annotation that makes the message list append-only — this is how the LLM retains full context across iterations.
- **Two exit conditions** from the loop: the LLM produces a plain-text answer, or the iteration safety counter hits its limit — whichever comes first.
- **Trade-off — token estimation vs precision**: rough character/4 heuristic is fast and dependency-free but inaccurate; a production system would capture real token counts from LLM API responses.
- **Trade-off — in-memory vs SQLite store**: in-memory is zero-config but loses history on restart and silently drops tool call history on replay; SQLite is persistent but requires a configured URL.
