# LangGraph Deep Dive — AI Agent

> **What:** LangGraph provides a stateful, graph-based framework for building AI agents
> **Why:** Explicit control flow, debugging, human-in-the-loop, state persistence
> **File:** `src/agent/graph.py`

---

## What LangGraph Solves

Traditional agent frameworks (e.g., LangChain AgentExecutor) use implicit loops:
- Agent calls LLM → LLM decides to call a tool → tool runs → repeat
- Hard to debug, no visibility into state, no checkpoints

LangGraph makes the control flow **explicit**:
- Nodes = functions (agent, tools)
- Edges = transitions (conditional routing)
- State = typed dictionary flowing through the graph

## The ReAct Pattern

ReAct = **Re**ason + **Act**

```
User: "What's the weather in Amsterdam?"

Step 1 (Reason): "I need to search for current weather in Amsterdam"
Step 2 (Act):    web_search("weather Amsterdam today")
Step 3 (Observe): "18°C, partly cloudy"
Step 4 (Respond): "The current weather in Amsterdam is 18°C and partly cloudy."
```

## Graph Definition

```python
workflow = StateGraph(AgentState)

# Nodes
workflow.add_node("agent", agent_node)    # Calls LLM
workflow.add_node("tools", ToolNode(tools))  # Executes tool calls

# Entry point
workflow.set_entry_point("agent")

# Conditional routing
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {"tools": "tools", "end": END}
)

# Tools always go back to agent
workflow.add_edge("tools", "agent")

graph = workflow.compile()
```

## State Management

LangGraph's `add_messages` reducer automatically appends new messages:

```python
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    iterations: int
    max_iterations: int
```

Each node returns a partial state update. LangGraph merges it:
```python
def agent_node(state):
    response = llm.invoke(state["messages"])
    return {"messages": [response], "iterations": state["iterations"] + 1}
```

## Iteration Limits

The `should_continue` function prevents infinite loops:

```python
def should_continue(state):
    if state["iterations"] >= state["max_iterations"]:
        return "end"  # Safety limit
    if last_message.tool_calls:
        return "tools"  # Agent wants to use a tool
    return "end"  # Agent is done
```

## Certification Relevance

| Topic | Connection |
|-------|-----------|
| State machines | LangGraph = explicit state machine |
| Event-driven architecture | Nodes + edges = event flow |
| Fault tolerance | Iteration limits = circuit breaker |
| Observability | State inspection at each node |
