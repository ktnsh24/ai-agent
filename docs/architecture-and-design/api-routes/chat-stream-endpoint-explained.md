# Chat Stream Endpoint — Deep Dive

> `POST /v1/chat/stream` — Send a message to the AI agent; receive a Server-Sent Events stream of thinking, tool calls, tokens, and a done signal.

> **Related docs:**
> - [Chat Endpoint (non-streaming)](chat-endpoint-explained.md) — canonical architecture walkthrough
> - [Architecture Overview](../architecture.md) — system design
> - [Conversations Endpoint](conversations-endpoint-explained.md) — history management

---

## Table of Contents

0. [Architecture Walkthrough (Start Here)](#architecture-walkthrough-start-here)
1. [Endpoint Summary](#endpoint-summary)
2. [SSE Event Sequence](#sse-event-sequence)
3. [Step 1 — Conversation Lookup or Creation](#step-1--conversation-lookup-or-creation)
4. [Step 2 — Agent Graph Execution](#step-2--agent-graph-execution)
5. [Step 3 — SSE Event Emission](#step-3--sse-event-emission)
6. [Step 4 — Conversation Store Write](#step-4--conversation-store-write)
7. [Condition Matrix](#condition-matrix)
8. [Honest Health Check](#honest-health-check)
9. [Real-World Example](#real-world-example)
10. [TL;DR](#tldr)

---

## Architecture Walkthrough (Start Here)

> This walkthrough explains what really happens when a request hits `POST /v1/chat/stream` — every design pattern, every branch, every known quirk. It focuses on what is different from the non-streaming chat endpoint; read [chat-endpoint-explained.md](chat-endpoint-explained.md) first for the shared assembly and ReAct loop mechanics.

---

### How the system is assembled at startup (before the first request arrives)

Assembly is identical to the non-streaming chat endpoint — the same five components built by the same **Factory Method + Strategy Pattern** lifespan hook. See the canonical walkthrough for the full provider table and tool registry detail. The key shared facts:

- LLM provider selected by `cloud_provider` (AWS/Azure/local); unknown value raises `ValueError` at startup
- Tool registry with `BuiltinToolProvider`; three tools gated by individual config flags; `MCPToolProvider` is dead wiring
- Conversation store: SQLite (persistent) or in-memory (lost on restart)
- Agent graph: LangGraph `StateGraph` with two nodes and ReAct loop
- CORS: all origins allowed; no auth, no rate limiting

> **Courier version.** The depot is set up in exactly the same way as the standard chat depot. The only difference is at the delivery window: instead of handing the customer one sealed envelope when the courier returns, the clerk relays each step of the delivery as it happens — a running commentary through a speaker at the window.

---

### The request pipeline — four steps in sequence

---

#### Step 1 — Conversation lookup or creation

This step is identical to the non-streaming endpoint. The handler checks `conversation_id` on the request:

- Provided and found in store → load full message history
- Provided and not found → `404` immediately, no generator starts
- Not provided → create new conversation (title = first 50 chars of message)

The user message is written to the store before the agent runs.

> **Courier version.** The clerk checks the tracking number as usual. If the customer has no record, they are turned away before the speaker even turns on. If the number is valid or new, the file is opened and the customer's note is filed immediately — even before the courier sets off.

---

#### Step 2 — Agent graph execution

The handler calls `agent_graph.run()` with the same arguments as the non-streaming endpoint. The graph executes synchronously and to completion before any token events are emitted. The full ReAct loop runs — all tool calls, all iterations — and the complete final response is held in memory.

This is the fundamental architectural trade-off of this endpoint: the `agent_graph.run()` call is blocking. The response generator cannot yield tokens while the graph is executing because LangGraph streaming is not wired up in this implementation. The SSE connection is open and silent during this period.

> **Courier version.** While the speaker is switched on, the clerk does not say anything yet — the courier is still out on the road completing all her runs. The customer is standing at the window hearing silence. Only after the courier returns with the final letter does the commentary begin.

---

#### Step 3 — SSE event emission

Once the graph finishes, the generator emits events in a fixed sequence using `sse_starlette.sse.EventSourceResponse`. The event types and their order:

| Event type | When emitted | Content |
|---|---|---|
| `thinking` | Immediately when the generator starts (before graph runs, actually) | Static "I'm processing your request" message |
| `tool_call` | One event per tool call, emitted in sequence | Tool name and arguments extracted from the finished message list |
| `token` | One event per space-separated word of the final response | Word from `response.message.split(" ")` |
| `done` | After all token events | The complete `AgentResponse` payload |
| `error` | If an exception occurs anywhere in the generator | Error message string |

**The `thinking` event is emitted before the graph runs** — it is a static signal, not a real indicator that the LLM is in a reasoning step. The customer sees "thinking" the instant they connect, before any work has started.

**Token streaming is simulated.** The full agent response is already complete when token events begin. The generator splits the response on spaces and emits one word per event in a tight loop with no delay. This mimics the visual appearance of streaming but is not true LLM token streaming — there is no progressive generation, no partial tokens, no back-pressure from the LLM. The client receives all words within milliseconds of the `thinking` event, after the silent blocking period ends.

**Worked example — event sequence for a two-tool-call response**

| # | Event type | Example content |
|---|---|---|
| 1 | `thinking` | "I'm processing your request..." |
| 2 | `tool_call` | `{name: "web_search", args: {query: "current weather London"}}` |
| 3 | `tool_call` | `{name: "calculator", args: {expression: "15 + 273"}}` |
| 4 | `token` | "The" |
| 5 | `token` | "temperature" |
| 6 | `token` | "in" |
| ... | `token` | (one per word) |
| N | `done` | Full `AgentResponse` payload |

> **Courier version.** When the courier returns with the final letter, the clerk picks up the microphone. She first says "thinking" (she already said this when the customer arrived — it was automatic). Then she reads out each trip the courier made: "First run: web_search for London weather. Second run: calculator, 15 plus 273." Then she reads the letter word by word through the speaker. Finally she says "done" and slides the full receipt under the window. The customer heard every word but the courier did all the work before any of it was spoken aloud.

---

#### Step 4 — Conversation store write

The assistant response is written to the store inside the generator, after the `done` event is emitted. This is a consequential design decision: the write happens inside the generator function body. If the generator raises an exception at any point before the write — during tool_call emission, during token emission, or during done emission — the assistant response is never stored.

The user message was written before the generator ran (Step 1), so a generator failure leaves the conversation with an orphaned user message and no reply.

> **Courier version.** The clerk files the assistant reply in the customer's folder only after she has finished speaking the whole letter aloud. If the microphone cuts out mid-word, the delivery receipt never gets filed — the customer's question is in the folder, but the answer is not.

---

## Endpoint Summary

| Property | Value |
|---|---|
| Method | `POST` |
| Path | `/v1/chat/stream` |
| Auth required | No |
| Rate limited | No |
| Response type | `text/event-stream` (SSE) |
| Real token streaming | No — simulated post-hoc word splitting |

---

## SSE Event Sequence

```
thinking → [tool_call × N] → token × W → done
                                        ↘ error (on failure)
```

- `thinking`: always first, static, emitted before graph runs
- `tool_call`: zero or more, one per tool used in this request
- `token`: one per space-separated word of the final response
- `done`: always last on success, carries full `AgentResponse`
- `error`: replaces `done` if an exception occurs

---

## Condition Matrix

| Scenario | What happens |
|---|---|
| `conversation_id` provided and found | Load history, run graph, stream events |
| `conversation_id` provided and not found | `404` before generator starts |
| No `conversation_id` | Create new conversation, stream events |
| Graph runs successfully | Emit thinking → tool_calls → tokens → done |
| Graph raises exception | `error` event emitted; store write skipped |
| Generator raises mid-emission | `error` event emitted; store write skipped if before write step |
| LLM used tools | `tool_call` events emitted for each tool |
| LLM used no tools | No `tool_call` events; direct to token emission |
| `max_iterations` reached | Graph exits; whatever partial response exists is emitted |

---

## 🩺 Honest Health Check

1. **Token streaming is simulated, not real.** The full agent response runs synchronously before any token is emitted — the client experiences a silent blocking period followed by a burst of word events; there is no true progressive generation. Fixing this requires wiring LangGraph's streaming callbacks through the generator.

2. **Conversation store write is inside the generator after `done`.** If the generator is interrupted — client disconnects, server exception, timeout — the assistant reply is never stored, leaving the conversation with an orphaned user message. Moving the write to a `finally` block or a post-generator hook would fix this.

3. **`thinking` event is a static lie.** It is emitted the moment the generator starts, not when the LLM enters a reasoning step. It gives the client a false impression of real-time progress during what is actually a blocking wait.

4. **Silent blocking period.** The SSE connection is held open with no events during the entire graph execution. Clients with short SSE timeouts may drop the connection before the `thinking` event has any follow-up. Emitting periodic keepalive events during graph execution would fix this.

5. **No auth, no rate limiting.** Identical to the non-streaming endpoint — any caller can open unlimited SSE connections and drive up LLM costs without restriction.

6. **In-memory store loses tool call history on replay.** Identical to the non-streaming endpoint — `ToolMessage` objects are not reconstructed by `InMemoryConversationStore`, so continued conversations via in-memory store do not include prior tool results in the LLM's context.

---

## Real-World Example

> Same flight-to-Paris question as the [chat endpoint example](chat-endpoint-explained.md#real-world-example), but via `POST /v1/chat/stream` to show the SSE event sequence in order.

---

### The request

```json
POST /v1/chat/stream
{
  "message": "How much does a flight to Paris cost right now, and convert that to GBP?",
  "conversation_id": null,
  "max_iterations": 5
}
```

No `conversation_id` — new thread.

---

### Step 1 — Conversation creation

Identical to the non-streaming endpoint. Store creates `id: "a3f7c2b1d4e8"`, `title: "How much does a flight to Pa"`. User message persisted before anything else runs. SSE connection is now open — but silent.

---

### Step 2 — Silent blocking period

The generator has not started. The graph runs synchronously and to completion first:

- Iteration 1: `web_search("London to Paris flight price today")` → `£89 EasyJet`
- Iteration 2: LLM produces plain text answer — no calculator needed

Client receives no events during this period. Full response is in memory. Generator begins.

---

### Step 3 — SSE event stream

Events arrive at the client in this fixed order:

```
event: thinking
data: {"content": "I'm processing your request..."}

event: tool_call
data: {"name": "web_search", "args": {"query": "London to Paris flight price today"}}

event: token
data: {"content": "Based"}

event: token
data: {"content": "on"}

event: token
data: {"content": "current"}

... (one event per space-separated word)

event: done
data: {
  "conversation_id": "a3f7c2b1d4e8",
  "message": "Based on current search results, flights from London to Paris start from £89 one-way on EasyJet. That price is already in GBP — no conversion required.",
  "tool_calls_made": [{"name": "web_search", "args": {"query": "London to Paris flight price today"}}],
  "iterations": 2,
  "status": "COMPLETE",
  "model": "claude-3-5-sonnet-v2",
  "total_tokens": 312,
  "latency_ms": 1840.0
}
```

**Key observations:**

- `thinking` fires immediately when the generator starts — the graph already finished by this point; the label is misleading
- The `tool_call` event is reconstructed from the finished message list, not emitted in real time when the tool ran
- All `token` events arrive as a burst with no delay between words — the full response was computed before the first token event
- `done` carries the same `AgentResponse` payload as a non-streaming `/v1/chat` call

---

### Step 4 — Conversation store write

After `done` is emitted, the assistant reply is written to the store: `role: assistant`, `content: "Based on current search results..."`. Conversation `updated_at` refreshed.

**If the client disconnects before this point** (mid-token stream, before `done`), the store write never happens — the conversation has the user's question with no reply.

---

## TL;DR

- **Same assembly as `/v1/chat`** — Factory Method + Strategy Pattern, five components, same ReAct loop — the only difference is the delivery window.
- **SSE via `EventSourceResponse`**: four event types (`thinking`, `tool_call`, `token`, `done`) in a fixed sequence; `error` replaces `done` on failure.
- **Token streaming is fake**: the graph runs synchronously and to completion; the response is then split on spaces and emitted word-by-word — this is UI theatre, not real LLM streaming.
- **Trade-off — store write inside generator**: convenient to implement but means a generator interruption leaves an orphaned user message with no reply in the conversation history.
- **Trade-off — `thinking` event before graph runs**: gives immediate feedback to the client but misrepresents when reasoning actually begins.
