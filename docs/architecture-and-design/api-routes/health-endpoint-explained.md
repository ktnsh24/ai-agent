# Health Endpoint — Deep Dive

> `GET /health` — Return the liveness status of the agent and its four core components.

> **Related docs:**
> - [Chat Endpoint](chat-endpoint-explained.md) — canonical architecture walkthrough
> - [Architecture Overview](../architecture.md) — system design

---

## Table of Contents

0. [Architecture Walkthrough (Start Here)](#architecture-walkthrough-start-here)
1. [Endpoint Summary](#endpoint-summary)
2. [Step 1 — Component Status Check](#step-1--component-status-check)
3. [Step 2 — Overall Status Determination](#step-2--overall-status-determination)
4. [What "Healthy" Actually Means Here](#what-healthy-actually-means-here)
5. [Condition Matrix](#condition-matrix)
6. [Honest Health Check](#honest-health-check)
7. [Real-World Example](#real-world-example)
8. [TL;DR](#tldr)

---

## Architecture Walkthrough (Start Here)

> This walkthrough explains what `GET /health` actually checks, how the overall status is determined, and what it cannot tell you. No code snippets, no file paths — but every design decision and gap is called out explicitly.

---

### How the system is assembled at startup (before the first request arrives)

The health endpoint does not build anything — it reads from what was already built. During startup, the **Factory Method + Strategy Pattern** lifespan hook constructs four components and stores them on `app.state`:

1. `llm_provider` — the LLM backend (Bedrock, Azure OpenAI, or Ollama)
2. `tool_registry` — the registered tool catalogue
3. `conversation_store` — SQLite or in-memory conversation history
4. `agent_graph` — the LangGraph `StateGraph` with the ReAct loop

If any of these failed to build (bad config, unreachable service, unknown provider), the application will not have started at all. By the time any request reaches the health endpoint, all four components are on `app.state` — the question the health check asks is only whether their current status strings contain the word `"error"`.

> **Courier version.** The health window is a notice board at the depot entrance. Every morning at startup, the manager pinned the status of each team member to the board. The health check is a clerk who reads those four pinned notes and checks whether any of them says "error". She does not go and find the team members, ask them to do a test run, or verify their tools are working — she just reads what is pinned.

---

### The request pipeline — two steps

---

#### Step 1 — Component status check

The handler accesses each of the four components on `app.state` and retrieves a status string from each. The check is a string-contains test: if the status string for a component contains the substring `"error"` (case-insensitive or case-sensitive — the check inspects the string representation), that component is flagged as degraded.

The four components checked:

| Component | What is accessed | Degraded condition |
|---|---|---|
| `llm_provider` | Status string from provider | Contains `"error"` |
| `tool_registry` | Status string from registry | Contains `"error"` |
| `conversation_store` | Status string from store | Contains `"error"` |
| `agent_graph` | Status string from graph | Contains `"error"` |

There are no deep probes. The health endpoint does not:
- Send a test message to the LLM and wait for a response
- Query the conversation store database to verify connectivity
- Call Tavily to verify the web_search tool is reachable
- Execute a test graph run through the ReAct loop

It only reads the status strings that were set at construction time.

> **Courier version.** The clerk reads the four pinned notes. If any note says "error" anywhere in the text, she marks that team member as degraded on the board. She does not knock on the courier's door to check she is awake, she does not call Tavily to check the search radio has signal, she does not open the filing cabinet to check the lock still works. She reads the four notes — that is the entire check.

---

#### Step 2 — Overall status determination

After checking all four components, the handler determines the overall status:

| Number of degraded components | Overall `status` returned |
|---|---|
| 0 | `"healthy"` |
| 1 or more | `"degraded"` |

The response includes both the overall status and the individual component statuses. A `"degraded"` response does not indicate which component failed — the caller must inspect the individual component fields to identify the problem.

This is more honest than a simple binary healthy/unhealthy — the system distinguishes between fully operational and partially degraded. However, `"degraded"` covers everything from one minor issue to all four components having errors.

> **Courier version.** If all four notes say nothing alarming, the notice board says "HEALTHY — all systems operational." If any note mentions an error, the board says "DEGRADED" — a worried customer knows something is wrong but has to read all four notes individually to find out what. There is no "CRITICAL" or "DOWN" — just healthy or degraded.

---

## Endpoint Summary

| Property | Value |
|---|---|
| Method | `GET` |
| Path | `/health` |
| Auth required | No |
| Rate limited | No |
| Probe depth | Shallow — string check only, no live probes |

---

## What "Healthy" Actually Means Here

`"healthy"` means: all four `app.state` components were constructed successfully at startup, and none of their status strings currently contains `"error"`.

It does NOT mean:
- The LLM is reachable and accepting requests
- The conversation store database is queryable
- The web_search tool can reach Tavily
- The calculator sandbox is functioning
- The database_query tool's SQLite file exists and is readable
- The agent graph can complete a ReAct loop

A "healthy" agent may fail on the very next `/v1/chat` request if, for example, the LLM's API credentials have expired since startup, or the SQLite file has been deleted.

---

## Condition Matrix

| Scenario | `status` returned |
|---|---|
| All four components have clean status strings | `"healthy"` |
| One component status string contains `"error"` | `"degraded"` |
| Two or more components degraded | `"degraded"` |
| All four components degraded | `"degraded"` |
| Component was never set on `app.state` (startup crash) | Application would not have started — this scenario cannot occur post-startup |
| LLM API credentials expired after startup | `"healthy"` — status string set at construction time unchanged |
| Tavily API unreachable | `"healthy"` — tool status string set at construction time unchanged |
| SQLite file deleted after startup | `"healthy"` — store status string set at construction time unchanged |

---

## 🩺 Honest Health Check

1. **No deep probes.** The health check reads static status strings set at startup — it cannot detect failures that occur after the application starts, such as expired LLM credentials, network partitions to Tavily, or a deleted SQLite file. Adding live probes (a minimal LLM ping, a `SELECT 1` against the store, a Tavily connectivity check) would make the health check genuinely useful for monitoring.

2. **`"degraded"` is the only failure signal.** There is no severity gradation — a single minor issue and a complete four-component failure both return `"degraded"`. A three-level status (`healthy`, `degraded`, `down`) with individual component codes would give operators more actionable information.

3. **No auth on the health endpoint.** This is intentional for load-balancer and monitoring use cases, but it means the component status strings (which may contain internal service names or configuration details) are publicly visible to any caller.

4. **Overall status does not use HTTP status codes.** A `"degraded"` response is returned with HTTP `200`. Some monitoring systems expect a non-`2xx` status code to signal degradation — the current design requires the monitoring system to parse the response body.

5. **String-contains check is fragile.** A component whose normal status message happens to contain the substring `"error"` (e.g., a message like "No errors found — operational") would be incorrectly flagged as degraded. A structured status enum or boolean flag would be more robust than substring matching.

---

## Real-World Example

Three scenarios showing the difference between healthy, degraded, and the deceptive gap between `"healthy"` and "actually working".

---

### Scenario A — All components healthy

Agent started with valid Bedrock credentials, SQLite store accessible, all tools enabled.

```
GET /health
```

Response:

```json
{
  "status": "healthy",
  "components": {
    "llm_provider": "BedrockProvider initialized — claude-3-5-sonnet-v2",
    "tool_registry": "3 tools registered — web_search, calculator, database_query",
    "conversation_store": "SQLiteConversationStore initialized",
    "agent_graph": "AgentGraph initialized"
  }
}
```

This guarantees the four components were constructed without errors at startup. It does not mean the LLM is currently reachable, the SQLite file still exists, or the next `/v1/chat` request will succeed.

---

### Scenario B — LLM provider degraded at startup

Agent started with an invalid Bedrock credential. The `BedrockProvider` constructor caught the error and recorded it in its status string.

```
GET /health
```

Response:

```json
{
  "status": "degraded",
  "components": {
    "llm_provider": "BedrockProvider error — invalid credentials",
    "tool_registry": "3 tools registered — web_search, calculator, database_query",
    "conversation_store": "SQLiteConversationStore initialized",
    "agent_graph": "AgentGraph error — LLM provider failed to initialize"
  }
}
```

One component has `"error"` in its status string → overall `"degraded"`. The caller must inspect individual component fields to find which one failed.

---

### Scenario C — Credentials expire after a healthy startup

Agent started cleanly (Scenario A result). Two hours later, Bedrock IAM credentials rotate and expire. Every `/v1/chat` request now fails with a credentials error.

```
GET /health
```

Response:

```json
{
  "status": "healthy",
  "components": {
    "llm_provider": "BedrockProvider initialized — claude-3-5-sonnet-v2",
    "tool_registry": "3 tools registered — web_search, calculator, database_query",
    "conversation_store": "SQLiteConversationStore initialized",
    "agent_graph": "AgentGraph initialized"
  }
}
```

Still `"healthy"` — status strings were set at construction time and are never updated. The health endpoint has no way to detect post-startup credential expiry. A monitoring system relying solely on this endpoint would see no signal despite all chat requests failing.

---

## TL;DR

- **Shallow string check only**: the health endpoint reads status strings from the four `app.state` components and checks for the substring `"error"` — no live probes, no actual connectivity tests.
- **`"degraded"`-aware**: unlike a simple binary healthy/unhealthy, the system can report `"degraded"` when at least one component has an error string — a more honest signal than always returning `"healthy"`.
- **`"healthy"` does not guarantee functionality**: a healthy response means components were constructed without errors at startup, not that they are currently operational — credentials can expire, files can be deleted, networks can partition.
- **Trade-off — shallow vs deep probes**: shallow checks are fast and have zero side effects (no LLM calls, no DB queries); deep probes would be accurate but add latency and cost to every health poll.
- **Trade-off — `"degraded"` as the only failure signal**: simple to implement and reason about, but provides no severity gradation — an operator sees degraded without knowing if it is one tool or all four components.
