# API Routes — Index

> A 1-page index to every HTTP route the AI Agent exposes. Click through to the per-endpoint deep dive for request/response schemas, internal flow, curl examples, and error tables.

> **Related docs:**
>
> - [Architecture Overview](architecture.md) — how the routes sit inside the agent
> - [Pydantic Models Reference](../reference/pydantic-models.md) — exact field-level types

---

## All Routes at a Glance

| Method | Path | Purpose | Deep dive | 🚚 Courier |
|--------|------|---------|-----------|-----------|
| `POST` | `/v1/chat` | Send a message; get agent response with tool calls and conversation history | [chat-endpoint-explained.md](api-routes/chat-endpoint-explained.md) | The main delivery window — slip in a parcel, the courier thinks, calls specialists if needed, and hands back a full response. |
| `POST` | `/v1/chat/stream` | Same as `/v1/chat` but delivered as SSE — simulated streaming, not real token streaming | [chat-stream-endpoint-explained.md](api-routes/chat-stream-endpoint-explained.md) | Same courier, same route — except the receipt prints line by line as each step completes rather than all at once at the door. |
| `GET` | `/v1/conversations` | List all conversations with metadata | [conversations-endpoint-explained.md](api-routes/conversations-endpoint-explained.md) | The dispatch log index — every open conversation thread the depot is currently tracking. |
| `GET` | `/v1/conversations/{id}` | Fetch a single conversation with its full message history | [conversations-endpoint-explained.md](api-routes/conversations-endpoint-explained.md) | Pull one thread from the log shelf and read every message exchanged, in order. |
| `DELETE` | `/v1/conversations/{id}` | Delete a conversation and all its messages | [conversations-endpoint-explained.md](api-routes/conversations-endpoint-explained.md) | Shred a thread — conversation record and every message inside it are removed from the depot. |
| `GET` | `/v1/tools` | List all tools registered in the agent's tool registry | [tools-endpoint-explained.md](api-routes/tools-endpoint-explained.md) | The specialist directory — every expert the courier can call mid-delivery and what problems each one solves. |
| `GET` | `/health` | Service health check — reports status of all four agent components | [health-endpoint-explained.md](api-routes/health-endpoint-explained.md) | The front-porch lamp — watchman glances at it without knocking, sees the courier, registry, store, and graph are all ready. |

---

## Wiring

Routes are mounted in `src/main.py` via `app.include_router(...)` for each module under `src/routes/`. The order is `health → chat → conversations → tools`.

There is no authentication middleware — the agent is designed for internal or development use. All routes are public.

Each route handler pulls the components it needs (agent graph, tool registry, conversation store) from `request.app.state`, which the lifespan hook in `src/main.py` populated at startup.

- 🚚 **Courier:** Every shipping window reaches into the same shared shelf of agent tools; no separate auth check runs on the way in.

---

## Where to Read Next

- For the agent's internal LangGraph pipeline (think → decide → act → observe) → [Architecture Overview](architecture.md).
- For the exact request/response field types across all routes → [Pydantic Models Reference](../reference/pydantic-models.md).
- For what the health check actually tests → [Health Endpoint](api-routes/health-endpoint-explained.md).
