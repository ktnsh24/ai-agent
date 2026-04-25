# Tool Use Deep Dive — AI Agent

> **What:** How the agent discovers, selects, and executes tools
>
> **Why:** Tools give LLMs access to real-time data, computation, and external systems
>
> **Files:** `src/tools/registry.py`, `src/tools/web_search.py`, `src/tools/calculator.py`, `src/tools/database_query.py`

---

## Tool Architecture

```
Tool Registry
├── BuiltinToolProvider
│   ├── web_search (Tavily / mock)
│   ├── calculator (safe AST evaluation)
│   └── database_query (SQLite read-only)
└── MCPToolProvider (Phase 4 — placeholder)
```

## How Tool Calling Works

1. **LLM receives tool schemas** — `llm.bind_tools(tools)` gives the LLM structured descriptions
2. **LLM decides to call a tool** — Returns an AIMessage with `tool_calls` field
3. **ToolNode executes** — LangGraph's ToolNode runs the tool and returns a ToolMessage
4. **Agent observes** — The result goes back to the agent for the next iteration

## Calculator: Safe Expression Evaluation

The calculator uses Python's AST parser to safely evaluate math:

```python
# Safe: parsed as AST nodes, only arithmetic allowed
safe_evaluate("2 + 3 * 4")      → 14
safe_evaluate("sqrt(16)")       → 4.0
safe_evaluate("2 ** 10")        → 1024

# Blocked: not in the allowed node types
safe_evaluate("__import__('os').system('rm -rf /')")  → ValueError
safe_evaluate("open('file.txt')")  → ValueError
```

This is critical for security — never use `eval()` on user input.

## Database Query: Read-Only SQL

The database tool enforces read-only access:

```python
BLOCKED_KEYWORDS = {"DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE"}

def _is_safe_query(query: str) -> bool:
    query_upper = query.strip().upper()
    for keyword in BLOCKED_KEYWORDS:
        if keyword in query_upper.split():
            return False
    return query_upper.startswith("SELECT") or query_upper.startswith("PRAGMA")
```

## Web Search: Tavily with Mock Fallback

```python
if settings.tavily_api_key:
    return TavilySearchTool(api_key=...)
else:
    return MockSearchTool()  # Returns fake results for development
```

## Cross-References

| Topic | Document |
|-------|----------|
| Agent loop | [LangGraph Deep Dive](langgraph-deep-dive.md) |
| Architecture | [Architecture](../architecture-and-design/architecture.md) |
| Setup | [Getting Started](../setup-and-tooling/getting-started.md) |
