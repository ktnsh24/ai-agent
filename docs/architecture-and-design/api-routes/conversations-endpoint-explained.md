# Conversations Endpoint — Deep Dive

> `GET /v1/conversations` · `GET /v1/conversations/{id}` · `DELETE /v1/conversations/{id}` — List, retrieve, and delete conversation history.

> **Related docs:**
> - [Chat Endpoint](chat-endpoint-explained.md) — canonical architecture walkthrough, including how conversations are created
> - [Architecture Overview](../architecture.md) — system design

---

## Table of Contents

0. [Architecture Walkthrough (Start Here)](#architecture-walkthrough-start-here)
1. [Endpoint Summary](#endpoint-summary)
2. [Step 1 — List All Conversations](#step-1--list-all-conversations)
3. [Step 2 — Get One Conversation with Messages](#step-2--get-one-conversation-with-messages)
4. [Step 3 — Delete a Conversation](#step-3--delete-a-conversation)
5. [SQLite vs In-Memory Store Comparison](#sqlite-vs-in-memory-store-comparison)
6. [Condition Matrix](#condition-matrix)
7. [Honest Health Check](#honest-health-check)
8. [TL;DR](#tldr)

---

## Architecture Walkthrough (Start Here)

> This walkthrough explains what really happens when a request hits any of the three conversations endpoints — every design decision, every store difference, and every known quirk. No code snippets, no file paths — but every strategy and trade-off that matters is called out explicitly.

---

### How the system is assembled at startup (before the first request arrives)

The conversations endpoints rely on a single component built during startup: the conversation store, constructed by a **Factory Method** that inspects the database URL in settings.

| Condition | Store created | Mechanism | Persistence |
|---|---|---|---|
| SQLite URL configured | `SQLiteConversationStore` | Async SQLAlchemy with two tables (`conversations`, `messages`) | Survives restarts; data is on disk |
| No SQLite URL | `InMemoryConversationStore` | Plain Python dict | Lost on every restart |

The two tables in `SQLiteConversationStore`:

- `conversations`: columns `id`, `title`, `created_at`, `updated_at`
- `messages`: columns `id`, `conversation_id`, `role`, `content`, `tool_name`, `tool_call_id`, `timestamp`

The `updated_at` column on `conversations` is kept current via a raw SQL `UPDATE conversations SET updated_at = :now` issued on every `add_message()` call — not via an ORM trigger.

No auth, no rate limiting. Any caller can list, read, or delete any conversation.

> **Courier version.** The filing cabinet is set up at depot opening. If a database path was configured, a real locked cabinet (SQLite) is used — folders survive when the depot closes for the night. If not, a clipboard on the wall (in-memory dict) is used — the clipboard is wiped clean every morning. The same cabinet handles three customer window slots: "list all folders", "show me a specific folder", and "shred a folder".

---

### The request pipeline — one step per operation

---

#### Step 1 — List all conversations (`GET /v1/conversations`)

The handler calls `conversation_store.get_all_conversations()`. The store returns a list of conversation summary objects — ID, title, `created_at`, `updated_at`. No message content is included in the list response; only metadata.

For `SQLiteConversationStore`, this is a `SELECT` on the `conversations` table — no join to `messages`. For `InMemoryConversationStore`, this iterates the in-memory dict and returns the summary for each entry.

There is no pagination. Every conversation in the store is returned in a single response. On a long-running SQLite store, this could be a large payload.

> **Courier version.** The clerk walks to the filing cabinet and reads out the label on every folder in order: tracking number, title, when it was created, when it was last updated. She does not open any folder or read any letters inside. If there are ten thousand folders, she reads all ten thousand labels in one go.

---

#### Step 2 — Get one conversation with messages (`GET /v1/conversations/{id}`)

The handler calls `conversation_store.get_conversation(id)` to verify the conversation exists, then calls `get_messages(id)` to retrieve the full message list. If the conversation is not found, the handler returns `404`.

**Message reconstruction differs by store:**

`SQLiteConversationStore.get_messages()` reconstructs full LangChain message objects by reading the `role` column from the `messages` table:

| `role` value in database | LangChain object reconstructed |
|---|---|
| `human` | `HumanMessage` |
| `assistant` | `AIMessage` |
| `system` | `SystemMessage` |
| `tool` | `ToolMessage` (with `tool_call_id` and `tool_name`) |

`InMemoryConversationStore.get_messages()` does not handle the `tool` role. `ToolMessage` objects are never reconstructed — tool call history is silently absent from any conversation replayed from the in-memory store. If a conversation had tool calls, those tool results will not appear in the response from `GET /v1/conversations/{id}` when the in-memory store is in use.

> **Courier version.** The clerk opens the requested folder and reads every letter inside in chronological order. With the locked cabinet (SQLite), she reads every type of letter — human notes, assistant replies, tool request slips, and tool result sheets. With the clipboard (in-memory), she reads human notes and assistant replies but quietly skips over all tool request slips and result sheets — they are simply not included in her reading.

---

#### Step 3 — Delete a conversation (`DELETE /v1/conversations/{id}`)

The handler calls `conversation_store.delete_conversation(id)`. If the conversation is not found, the handler returns `404`.

Deletion is a two-step cascade:

1. Delete all rows from the `messages` table where `conversation_id` matches
2. Delete the row from the `conversations` table where `id` matches

Both steps run in the same database transaction for `SQLiteConversationStore`. For `InMemoryConversationStore`, the conversation entry is removed from the dict; messages are stored within the same dict entry, so they are removed together.

There is no soft delete, no archive, no recycle bin. Deletion is permanent and immediate. No confirmation is required — a single `DELETE` HTTP request with the conversation ID is sufficient.

> **Courier version.** The clerk takes the folder out of the cabinet, shreds every letter inside it first, then shreds the folder itself. With the locked cabinet (SQLite), both steps happen as one atomic action — either both succeed or neither does. With the clipboard (in-memory), tearing up the clipboard entry removes everything at once. Either way, there is no recovery: the folder and all its letters are gone.

---

## Endpoint Summary

| Endpoint | Method | Auth | Rate limited | Returns |
|---|---|---|---|---|
| `/v1/conversations` | `GET` | No | No | List of all conversation summaries |
| `/v1/conversations/{id}` | `GET` | No | No | Full conversation with reconstructed message list; `404` if not found |
| `/v1/conversations/{id}` | `DELETE` | No | No | `200` on success; `404` if not found |

---

## SQLite vs In-Memory Store Comparison

| Behaviour | SQLiteConversationStore | InMemoryConversationStore |
|---|---|---|
| Persistence across restart | Yes | No |
| `ToolMessage` reconstruction on `GET /conversations/{id}` | Yes — full tool call history visible | No — tool call history silently absent |
| `DELETE` atomicity | Transactional (messages then conversation) | Dict removal (atomic in Python GIL) |
| `updated_at` tracking | Yes — raw SQL UPDATE on every `add_message()` | Implementation-dependent |
| Scalability | Bounded by SQLite file size and no connection pooling | Bounded by process memory |

---

## Condition Matrix

| Scenario | What happens |
|---|---|
| `GET /v1/conversations` — store has conversations | List of summaries returned; no message content |
| `GET /v1/conversations` — store is empty | Empty list returned |
| `GET /v1/conversations/{id}` — ID found, SQLite store | Full conversation including ToolMessage objects |
| `GET /v1/conversations/{id}` — ID found, in-memory store | Full conversation excluding ToolMessage objects |
| `GET /v1/conversations/{id}` — ID not found | `404` |
| `DELETE /v1/conversations/{id}` — ID found | Messages deleted first, then conversation row; `200` |
| `DELETE /v1/conversations/{id}` — ID not found | `404` |
| In-memory store, server restarts | All conversations gone; subsequent GET returns empty list |

---

## 🩺 Honest Health Check

1. **`GET /v1/conversations` has no pagination.** All conversations are returned in one response — on a store with thousands of long-running conversations this is an unbounded payload. Adding `limit`/`offset` or cursor-based pagination would fix this.

2. **In-memory store silently drops tool call history.** `ToolMessage` objects are not reconstructed by `InMemoryConversationStore.get_messages()` — a caller reading a conversation with tool calls from the in-memory store will see an incomplete message list with no indication that messages are missing.

3. **No authentication.** Any caller can list all conversations (including those belonging to other users), read the full message history of any conversation, and permanently delete any conversation without credentials.

4. **No soft delete or audit trail.** `DELETE /v1/conversations/{id}` is immediately destructive with no recovery path — a mistaken deletion permanently removes the conversation and all its messages.

5. **No connection pooling in SQLiteConversationStore.** The store opens and closes a database connection per operation — under concurrent load this creates contention on the SQLite file. A connection pool or a dedicated async database session would fix this.

6. **`updated_at` is updated on every message add, not just on user turns.** Assistant replies and tool messages trigger a raw `UPDATE` on the conversation row — this is correct behaviour for "last activity" semantics but means `updated_at` reflects the last assistant write, not the last human interaction.

---

## TL;DR

- **Factory Method** selects `SQLiteConversationStore` (persistent, full fidelity) or `InMemoryConversationStore` (ephemeral, drops tool history) at startup — the Strategy Pattern means all three endpoints call the same interface regardless.
- **`GET /v1/conversations/{id}`** reconstructs LangChain message objects from the store; SQLite reconstructs all four types including `ToolMessage`; in-memory silently omits tool call history.
- **`DELETE /v1/conversations/{id}`** cascades: messages deleted first, conversation row second, transactionally in SQLite.
- **Trade-off — no pagination on list endpoint**: zero-config simplicity at the cost of unbounded response size.
- **Trade-off — in-memory `ToolMessage` gap**: no persistence requirement is met but replay fidelity is silently compromised.
