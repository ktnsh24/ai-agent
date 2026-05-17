# Tools Endpoint — Deep Dive

> `GET /v1/tools` — Return the list of tools registered with the agent at startup.

> **Related docs:**
> - [Chat Endpoint](chat-endpoint-explained.md) — canonical architecture walkthrough, including how tools are invoked during the ReAct loop
> - [Architecture Overview](../architecture.md) — system design

---

## Table of Contents

0. [Architecture Walkthrough (Start Here)](#architecture-walkthrough-start-here)
1. [Endpoint Summary](#endpoint-summary)
2. [Step 1 — Tool Registry Snapshot](#step-1--tool-registry-snapshot)
3. [Tool Deep Dives](#tool-deep-dives)
   - [web_search](#web_search)
   - [calculator](#calculator)
   - [database_query](#database_query)
4. [MCP Dead Wiring](#mcp-dead-wiring)
5. [Condition Matrix](#condition-matrix)
6. [Honest Health Check](#honest-health-check)
7. [Real-World Example](#real-world-example)
8. [TL;DR](#tldr)

---

## Architecture Walkthrough (Start Here)

> This walkthrough explains what the `GET /v1/tools` endpoint actually returns, how the tool registry is assembled at startup, what each tool actually does, and where the known flaws are. No code snippets, no file paths — but every design decision and trade-off is named explicitly.

---

### How the system is assembled at startup (before the first request arrives)

The tool registry is built once during startup by a **Factory Method** that constructs a `ToolRegistry` and registers providers against it. This follows the **Strategy Pattern**: each provider implements the same abstract `ToolProvider` interface; the registry calls `get_tools()` on each registered provider and aggregates the results. The LLM later receives all aggregated tools as function definitions.

**Provider registration follows two rules:**

1. `BuiltinToolProvider` is always registered — it is unconditional.
2. `MCPToolProvider` is registered only if `settings.mcp_enabled=True`.

Within `BuiltinToolProvider`, each tool is individually gated by a config flag. A tool that is disabled by its flag is never added to the registry and is never visible to the LLM.

| Tool | Config flag | Registered when |
|---|---|---|
| `web_search` | `tool_web_search_enabled` | Flag is `True` |
| `calculator` | `tool_calculator_enabled` | Flag is `True` |
| `database_query` | `tool_database_query_enabled` | Flag is `True` |

**What `GET /v1/tools` returns** is a snapshot of the registry at the moment the request arrives. The registry is assembled once at startup and never mutated — enabling or disabling a tool requires an application restart.

> **Courier version.** At depot opening, the manager bolts tools onto the courier van — a search radio, a calculator clipboard, a database terminal — each only if the relevant dashboard switch is on. A second slot exists for MCP tools, but the connection cable for that slot was never finished (Phase 4 stub). When a customer asks "what tools does your courier carry?", the clerk reads back the list of bolted-on tools exactly as they were fitted at opening time. The list never changes mid-shift.

---

### The request pipeline — one step

---

#### Step 1 — Tool registry snapshot

The handler calls `tool_registry.get_tools()` from `app.state` and returns the result. The response is the list of tool names and descriptions as they were registered at startup. No computation, no I/O, no database access.

> **Courier version.** The clerk walks to the van, reads the label on each bolted-on tool, and reports the list back to the customer. She does not check whether the tools are working — she just reads the labels.

---

## Endpoint Summary

| Property | Value |
|---|---|
| Method | `GET` |
| Path | `/v1/tools` |
| Auth required | No |
| Rate limited | No |
| Mutable | No — snapshot of startup state |

---

## Tool Deep Dives

### web_search

**What it does:** Queries the web for a given search string and returns up to 5 results.

**Two concrete strategies — selected at startup by Factory Method:**

| Condition | Strategy used | Behaviour |
|---|---|---|
| `settings.tavily_api_key` is set | Real Tavily search | Sends query to Tavily API; returns up to 5 results with title, URL, snippet |
| No `tavily_api_key` | Mock search | Returns hardcoded responses matched by keyword |

**Mock keyword matching table:**

| Keyword in query | Mock response returned |
|---|---|
| "weather" | Hardcoded weather-like string |
| "news" | Hardcoded news-like string |
| anything else | Hardcoded "default" response |

The mock has exactly three branches. Any query that does not contain "weather" or "news" falls to the default response, regardless of what was actually asked.

**Error handling:** If the Tavily API call raises an exception, the exception is caught and an error string is returned to the LLM. There is no retry — one failure, one error string. The LLM decides what to do next (typically it will acknowledge the failure in its response).

> **Courier version.** The search radio has two modes. With a valid Tavily licence, it contacts the real broadcast network and returns up to five live results. Without a licence, it plays one of three pre-recorded tapes: a weather tape, a news tape, or a generic "sorry, I don't have that" tape. If the radio fails mid-transmission, the courier notes down "search failed" and continues with her other work.

---

### calculator

**What it does:** Evaluates a mathematical expression and returns the numeric result.

**Implementation strategy: AST safe-eval sandbox**

The tool parses the input expression using Python's `ast` module — building an abstract syntax tree — then walks the tree with a custom `_safe_eval()` function. There is no `eval()` call anywhere. This is a genuine sandbox, not security by obscurity.

**Whitelist of allowed operators:**

| Category | Allowed |
|---|---|
| Binary operators | `+`, `-`, `*`, `/`, `//`, `%`, `**` |
| Unary operators | `-`, `+` |

**Whitelist of allowed functions:**

| Function | Meaning |
|---|---|
| `sqrt` | Square root |
| `abs` | Absolute value |
| `round` | Round to nearest integer |
| `sin`, `cos`, `tan` | Trigonometric functions |
| `log`, `log10` | Natural and base-10 logarithm |
| `pi`, `e` | Mathematical constants |

Any expression containing a node type not in these whitelists raises a `ValueError`. The error string is returned to the LLM — not raised to the caller. Two additional errors are caught explicitly: division by zero and arithmetic overflow. Both return descriptive error strings to the LLM rather than raising exceptions.

**What the AST sandbox prevents:** arbitrary Python execution (`import`, function definitions, attribute access, subscript access, comprehensions). An input like `__import__('os').system('rm -rf /')` would fail at the `ast` walk step — `__import__` is a `Call` node referencing a `Name` not in the whitelist.

> **Courier version.** The calculator clipboard has a strict rulebook: the courier can add, subtract, multiply, divide, and use a list of named scientific functions. She works through the expression step by step using the rulebook. If the expression asks her to do anything not in the rulebook — run a program, access the filing system, call a phone number — she writes "invalid operation" and stops. She never runs arbitrary instructions.

---

### database_query

**What it does:** Executes a read-only SQL query against a bundled SQLite sample database and returns up to 50 rows.

**Sample database schema:**

| Table | Columns | Sample data |
|---|---|---|
| `products` | id, name, category, price, stock | 10 products across Electronics, Furniture, Books |
| `orders` | id, product_id, quantity, total_price, order_date | 10 orders referencing products |

The SQLite file is created on first tool registration if it does not already exist. Connection is opened and closed per query — no connection pooling.

**Safety gate — keyword-split check:**

Before executing any query, the tool applies a two-part safety rule:

1. The query must start with `SELECT` or `PRAGMA` (case-insensitive check)
2. The uppercased query must not contain any of these keywords as whitespace-split tokens: `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `CREATE`, `TRUNCATE`, `EXEC`

**Known bypass — no space before keyword:**

The keyword check splits the uppercased query on whitespace. A query like `SELECT 1;DELETE FROM products` uppercases to `SELECT 1;DELETE FROM PRODUCTS`. When split on whitespace, the tokens are `['SELECT', '1;DELETE', 'FROM', 'PRODUCTS']`. The string `'DELETE'` is not in that token list because it is attached to `'1;DELETE'` with no preceding space. The query passes the guard and is executed, deleting all rows from `products`.

This is a real SQL injection bypass via semicolon-separated statements with no whitespace before the dangerous keyword. It is documented here so engineers know it exists.

**Results are truncated to 50 rows.** No indication is given to the LLM that results were truncated — the LLM sees a 50-row result and has no way to know whether more rows exist.

> **Courier version.** The database terminal has a guard at the door who checks two things: the query must start with "SELECT" or "PRAGMA", and none of the dangerous words (DROP, DELETE, UPDATE...) can appear as a full word with a space before it. The guard is checking for "space-DELETE" — if someone writes "1;DELETE" with no space, the guard does not spot it. A courier who knows this trick can slip a destructive command past the guard by hiding it after a semicolon with no space. This is a known flaw in the guard's rulebook.

---

## MCP Dead Wiring

`MCPToolProvider` is registered in the tool registry if `settings.mcp_enabled=True`. It appears as a provider in the registry. However:

- Its `connect()` method logs "not yet implemented (Phase 4)" and returns immediately — no MCP connection is ever established
- Its `get_tools()` method always returns an empty list

Setting `mcp_enabled=True` adds the provider object to the registry but contributes zero tools. The `GET /v1/tools` response will not include any MCP tools regardless of the flag value. This is a Phase 4 placeholder — the wiring exists but the implementation does not.

> **Courier version.** There is an empty slot on the van labelled "MCP tools". The slot exists, the label is there, the provider is registered. But the cable to connect the MCP tool box was never finished — the box is on order for Phase 4. Until then, the slot is always empty, and the customer list of tools never includes anything from it.

---

## Condition Matrix

| Scenario | What happens |
|---|---|
| All three tools enabled | Three tools returned by `GET /v1/tools` |
| `tool_web_search_enabled=False` | `web_search` absent from list |
| `tool_calculator_enabled=False` | `calculator` absent from list |
| `tool_database_query_enabled=False` | `database_query` absent from list |
| All tools disabled | Empty list returned |
| `mcp_enabled=True` | `MCPToolProvider` registered; zero MCP tools added to list |
| `tavily_api_key` set | `web_search` uses real Tavily API |
| No `tavily_api_key` | `web_search` uses 3-keyword mock |
| Calculator expression uses non-whitelisted node | `ValueError` returned as string to LLM |
| Calculator division by zero | Error string returned to LLM |
| Database query starts with `SELECT` | Executed; up to 50 rows returned |
| Database query `SELECT 1;DELETE FROM products` | Passes keyword guard (bypass); executes |
| Database query starts with `DROP` | Blocked by keyword guard; error string returned to LLM |

---

## 🩺 Honest Health Check

1. **`database_query` keyword guard can be bypassed.** A semicolon-separated statement with no space before a dangerous keyword passes the whitespace-split check — `SELECT 1;DELETE FROM products` is a real injection vector. Parameterised queries, a proper SQL parser, or disabling multi-statement execution would fix this.

2. **`GET /v1/tools` does not verify tool health.** The endpoint returns the registry snapshot without checking whether Tavily is reachable, whether the SQLite database file is accessible, or whether the calculator sandbox is operational. A degraded tool (e.g., Tavily unreachable) is indistinguishable from a healthy one in the response.

3. **No `tavily_api_key` means silent mock fallback.** The LLM is told it has a `web_search` tool but receives mock responses for all but three keywords. A caller has no way to know from the tool list or the response whether real or mock results were used.

4. **Results truncated at 50 rows with no indication.** The LLM receives a 50-row result from `database_query` with no signal that the result set was truncated — it may draw incorrect conclusions from an incomplete dataset.

5. **MCP flag creates false expectations.** `mcp_enabled=True` in config suggests MCP tools are active, but no MCP tools are ever registered. The flag is misleading until Phase 4 is implemented.

6. **Tool list is immutable without restart.** Enabling or disabling a tool, adding a new tool, or changing tool config requires an application restart — there is no dynamic tool registration API.

---

## Real-World Example

Three scenarios: full tool set, partial tool set, and mock mode masquerading as real search.

---

### Scenario A — All three tools enabled, Tavily key configured

Config: `tool_web_search_enabled=True`, `tool_calculator_enabled=True`, `tool_database_query_enabled=True`, `tavily_api_key` set.

```
GET /v1/tools
```

Response:

```json
[
  {
    "name": "web_search",
    "description": "Search the web for current information.",
    "parameters": {
      "type": "object",
      "properties": {"query": {"type": "string"}},
      "required": ["query"]
    }
  },
  {
    "name": "calculator",
    "description": "Evaluate a mathematical expression safely.",
    "parameters": {
      "type": "object",
      "properties": {"expression": {"type": "string"}},
      "required": ["expression"]
    }
  },
  {
    "name": "database_query",
    "description": "Query the sample product and orders database.",
    "parameters": {
      "type": "object",
      "properties": {"query": {"type": "string"}},
      "required": ["query"]
    }
  }
]
```

These three schemas are injected into every LLM call via `.bind_tools()` at graph construction time. The LLM can include any of these in its `tool_calls` field.

---

### Scenario B — Only calculator enabled

Config: `tool_web_search_enabled=False`, `tool_calculator_enabled=True`, `tool_database_query_enabled=False`.

```
GET /v1/tools  →  [{"name": "calculator", ...}]
```

Only the calculator schema is injected into LLM calls. If a user asks `"What is the current price of a flight to Paris?"`, the LLM has no `web_search` function definition available — it will answer from training data or tell the user it cannot search. No tool call will be attempted because the schema is not in scope.

---

### Scenario C — web_search enabled but no Tavily key (mock mode)

Config: `tool_web_search_enabled=True`, `tavily_api_key` not set.

`GET /v1/tools` still returns `web_search` in the list — the mock strategy is selected silently at startup and is not reflected in the tool name or description.

When the LLM calls `web_search("London to Paris flight price today")`, the mock receives the query, finds no match for `"weather"` or `"news"`, and returns the default hardcoded response:

```
"Here is some general information about your search query..."
```

The LLM bases its answer on this mock result. Neither the tool list nor the response body contains any indicator that mock mode is active — the caller has no way to distinguish a real Tavily search from a hardcoded placeholder.

---

## TL;DR

- **Strategy Pattern on tool registry**: `BuiltinToolProvider` always registered; `MCPToolProvider` conditionally registered but permanently a stub (dead wiring); three built-in tools each individually gated by a config flag.
- **`web_search`**: Factory Method selects real Tavily vs 3-keyword mock based on API key presence; no retry on Tavily failure.
- **`calculator`**: Genuine AST safe-eval sandbox — no `eval()`, whitelisted operators and functions only; division-by-zero and overflow caught explicitly.
- **`database_query`**: Keyword-split safety guard with a known bypass — `SELECT 1;DELETE FROM products` passes the whitespace-split check via semicolon injection with no preceding space.
- **Trade-off — simplicity vs security on `database_query`**: a whitespace-split keyword check is easy to implement but easy to bypass; a proper SQL parser or an ORM with parameterised queries would close the gap.
