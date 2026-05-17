# Understanding the ai-agent Code — A Plain-English Walkthrough

> This doc is a study guide for the ai-agent repo only.
> Every explanation uses a concrete example with real inputs and real outputs.
> No abstract summaries — only "here is what flows in, here is what comes out."

---

## Table of Contents

1. [What this repo is made of — the five real parts](#what-this-repo-is-made-of--the-five-real-parts)
2. [What to learn in order](#what-to-learn-in-order)
3. [graph.py — line by line](#graphpy--line-by-line)
   - [The big picture](#the-big-picture)
   - [AgentState — the shared memory bag](#agentstate--the-shared-memory-bag)
   - [bind\_tools — where it comes from](#bind_tools--where-it-comes-from)
   - [agent\_node — what happens at the agent station](#agent_node--what-happens-at-the-agent-station)
   - [should\_continue — the switch at the station](#should_continue--the-switch-at-the-station)
   - [Building the actual track](#building-the-actual-track)
   - [run() — how a real message enters and exits](#run--how-a-real-message-enters-and-exits)
4. [Full example with two tools — every message shape shown](#full-example-with-two-tools--every-message-shape-shown)
5. [The one line that makes the loop work](#the-one-line-that-makes-the-loop-work)

---

## What this repo is made of — the five real parts

The ai-agent repo has five moving parts. Each part has one job.

| Part | Folder / file | One-line job |
| --- | --- | --- |
| **Tools** | `src/tools/calculator.py`, `web_search.py`, `database_query.py` | The actual functions the agent can call — math, web, database |
| **Agent loop** | `src/agent/graph.py` | The brain — LLM reads messages, decides which tool to call, loops until done |
| **Memory** | `src/agent/conversation.py` | Saves every message to SQLite so the agent remembers past conversations |
| **Tool registry** | `src/tools/registry.py` | Decides which tools are active — reads config flags, assembles the list |
| **API** | `src/routes/chat.py` | The door — receives your HTTP request, calls the agent loop, returns the answer |

How they connect when you send a message:

```text
Your HTTP request
  │
  ▼
chat.py (API)          ← the door
  │
  ▼
graph.py (agent loop)  ← the brain
  │  reads tools from registry.py
  │  reads history from conversation.py
  │  calls tools from src/tools/
  ▼
final answer → back through chat.py → HTTP response
```

---

## What to learn in order

Work through the files in this order. Each one builds on the last.

| Step | File | Time needed | What you will know after |
| --- | --- | --- | --- |
| 1 | `src/tools/calculator.py` | 30 minutes | What a tool is, what `@tool` does, why safe eval matters |
| 2 | `src/agent/graph.py` | 1 hour | How the LLM loop works, what controls the flow |
| 3 | `src/agent/conversation.py` | 45 minutes | How memory is stored, what SQLite is used for |
| 4 | `src/tools/registry.py` | 30 minutes | How tools are turned on/off by config |
| 5 | `src/routes/chat.py` | 30 minutes | What the API does, how streaming works |

---

## graph.py — line by line

### The big picture

Think of LangGraph like a small train track with two stations:

```text
Station "agent"  ──────►  Station "tools"
      ▲                          │
      └──────────────────────────┘
```

The train (your messages) starts at "agent". The LLM reads the messages and decides: do I need a tool?

- If yes → train goes to "tools", the tool runs, the result is added to the messages, train goes back to "agent".
- If no → train stops at `END` and the answer is returned.

This loops until the LLM says "I am done."

---

### AgentState — the shared memory bag

```python
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    iterations: int
    max_iterations: int
    tool_calls_made: list[ToolCall]
```

This is the bag that travels with the train. Every station reads it and adds to it.

| Key | Type | What it holds |
| --- | --- | --- |
| `messages` | list of messages | The full conversation — every human message, every LLM reply, every tool result |
| `iterations` | int | Counter. Starts at 0. Goes up by 1 every time the "agent" station runs. |
| `max_iterations` | int | Safety limit. If `iterations` reaches this, the loop stops. Without this a broken LLM could loop forever. |
| `tool_calls_made` | list | A log of every tool called — shown in the final response metadata. |

`add_messages` in the annotation means: "when you add a new message to this list, append it — do not replace the whole list."

---

### bind\_tools — where it comes from

```python
llm = self.llm_provider.get_chat_model()   # returns BaseChatModel
llm_with_tools = llm.bind_tools(tools)
```

`get_chat_model()` returns a `BaseChatModel`. That is a LangChain class:

```python
from langchain_core.language_models import BaseChatModel
```

`bind_tools` is **a method that LangChain already put on `BaseChatModel`**. You did not write it. LangChain wrote it. It lives inside the `langchain-core` installed package — you never open that file.

What it does: it converts your Python tool functions (calculator, web\_search, database\_query) into JSON schemas and attaches them to every API call. When the LLM (Claude or GPT) sees those schemas, it knows exactly what format to use when it wants to call a tool.

The chain of ownership:

```text
your provider.py
  └── ChatBedrock (from langchain_aws)
        └── extends BaseChatModel (from langchain_core)
              └── .bind_tools() lives here — you never touch this file
```

Without `bind_tools`, the LLM is a plain chatbot. With it, the LLM can request tool calls in a structured format.

---

### agent\_node — what happens at the agent station

```python
def agent_node(state: AgentState) -> dict:
    messages = state["messages"]
    response = llm_with_tools.invoke(messages)
    return {
        "messages": [response],
        "iterations": state["iterations"] + 1,
    }
```

This runs every time the train arrives at the "agent" station.

1. `state["messages"]` — takes all messages so far (your question + any previous tool results).
1. `llm_with_tools.invoke(messages)` — sends all messages to the LLM and waits for a reply.
1. The reply is an `AIMessage`. It has two possible shapes:

**Shape A — LLM wants to call a tool (content is empty):**

```python
AIMessage(
    content="",           # empty — LLM is not answering yet
    tool_calls=[{
        "id": "call_abc123",
        "name": "calculator",
        "args": {"expression": "sqrt(144)"}
    }]
)
```

**Shape B — LLM is ready to give the final answer (tool\_calls is empty):**

```python
AIMessage(
    content="The square root of 144 is 12.",
    tool_calls=[]          # empty — no tool needed
)
```

1. The function adds the reply to `messages` and adds 1 to `iterations`.

---

### should\_continue — the switch at the station

```python
def should_continue(state: AgentState) -> str:
    messages = state["messages"]
    last_message = messages[-1]

    if state["iterations"] >= state["max_iterations"]:
        return "end"

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"

    return "end"
```

After every `agent_node` run, LangGraph calls this function to decide where the train goes next. It returns a string — the name of the next station.

| Condition | Return value | What happens |
| --- | --- | --- |
| `iterations >= max_iterations` | `"end"` | Safety stop — loop has run too many times |
| `last_message.tool_calls` is not empty | `"tools"` | LLM wants to call a tool — go run it |
| Everything else | `"end"` | LLM gave a final answer — we are done |

---

### Building the actual track

```python
workflow = StateGraph(AgentState)

workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_node)

workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent",
    should_continue,
    {"tools": "tools", "end": END},
)
workflow.add_edge("tools", "agent")

return workflow.compile()
```

| Line | What it means |
| --- | --- |
| `StateGraph(AgentState)` | Create a new empty track. It will carry `AgentState` bags. |
| `add_node("agent", agent_node)` | Add a station called "agent". When train arrives, run `agent_node`. |
| `add_node("tools", tool_node)` | Add a station called "tools". When train arrives, run the tool. |
| `set_entry_point("agent")` | The train always starts at "agent". |
| `add_conditional_edges(...)` | After "agent", ask `should_continue`. Route based on what it returns. |
| `add_edge("tools", "agent")` | After "tools", always go back to "agent". No conditions. Always loop back. |
| `workflow.compile()` | Lock the track. Make it ready to run. |

The track as a diagram:

```text
START
  │
  ▼
"agent" (agent_node runs — LLM decides)
  │
  ├── should_continue returns "tools" ──► "tools" (ToolNode runs the Python function)
  │                                           │
  │                                           └──────────────────── back to "agent"
  │
  └── should_continue returns "end" ──► END (return the final answer)
```

---

### run() — how a real message enters and exits

```python
messages: list[BaseMessage] = [SystemMessage(content=SYSTEM_PROMPT)]
if conversation_history:
    messages.extend(conversation_history)
messages.append(HumanMessage(content=user_message))
```

Before the loop starts, `run()` builds the message list:

1. First — always the system prompt (instructions for the LLM).
1. Then — all previous messages from this conversation (so the LLM remembers context).
1. Then — your new message at the end.

```python
initial_state: AgentState = {
    "messages": messages,
    "iterations": 0,
    "max_iterations": max_iter,
    "tool_calls_made": [],
}

result = await self._graph.ainvoke(initial_state)
```

This puts the bag on the train and starts it. `ainvoke` means "run async" (non-blocking). LangGraph runs the whole loop and gives you back the final state when done.

```python
for msg in reversed(result_messages):
    if isinstance(msg, AIMessage) and msg.content:
        final_message = msg.content
        break
```

After the loop ends, this scans from the end of the message list backwards. The first `AIMessage` that has text in `content` is the final answer. That gets returned to the user.

---

## Full example with two tools — every message shape shown

**The question:** "What is the price of the product named 'Laptop Pro', and then calculate 15% tax on that price."

This forces the agent to call `database_query` first, then `calculator`.

---

### Before the loop — initial state

`run()` builds:

```python
initial_state = {
    "messages": [
        SystemMessage(content="You are a helpful AI assistant..."),
        HumanMessage(content="What is the price of 'Laptop Pro', then calculate 15% tax on it.")
    ],
    "iterations": 0,
    "max_iterations": 10,
    "tool_calls_made": []
}
```

---

### Loop iteration 1 — agent\_node runs

```python
messages = state["messages"]                # 2 messages
response = llm_with_tools.invoke(messages)  # LLM reads them
```

LLM decides: "I need to query the database first — I do not know the price."

**AIMessage shape — Tool Call 1:**

```python
AIMessage(
    content="",        # EMPTY — LLM is not answering yet
    tool_calls=[
        {
            "id": "call_abc123",
            "name": "database_query",
            "args": {
                "query": "SELECT price FROM products WHERE name = 'Laptop Pro'"
            }
        }
    ]
)
```

Messages bag after iteration 1:

```text
1. SystemMessage   ("You are a helpful AI...")
2. HumanMessage    ("What is the price of 'Laptop Pro'...")
3. AIMessage       (content="", tool_calls=[database_query]) ← NEW
iterations = 1
```

`should_continue` sees `tool_calls` is not empty → returns `"tools"`. Train goes to the "tools" station.

---

### ToolNode runs — Tool Call 1 executes

LangGraph reads `tool_calls` from the last `AIMessage`. It finds `"database_query"`, finds the Python function, calls it:

```python
database_query(query="SELECT price FROM products WHERE name = 'Laptop Pro'")
# returns: "Results: [{'price': 1200.00}]"
```

**ToolMessage shape — Result of Tool Call 1:**

```python
ToolMessage(
    content="Results: [{'price': 1200.00}]",
    tool_call_id="call_abc123",   # must match the id from the AIMessage above
    name="database_query"
)
```

`tool_call_id` is how the LLM knows which result belongs to which tool call. Two tool calls = two different ids.

Messages bag after Tool Call 1:

```text
1. SystemMessage   ("You are a helpful AI...")
2. HumanMessage    ("What is the price of 'Laptop Pro'...")
3. AIMessage       (content="", tool_calls=[database_query])
4. ToolMessage     (content="Results: [{'price': 1200.00}]", id="call_abc123") ← NEW
iterations = 1
```

---

### Loop iteration 2 — agent\_node runs again

Train goes back to "agent". `agent_node` runs:

```python
messages = state["messages"]                # now 4 messages
response = llm_with_tools.invoke(messages)  # LLM reads all 4
```

LLM now knows the price is 1200. It decides: "Now I need to calculate 15% tax."

**AIMessage shape — Tool Call 2:**

```python
AIMessage(
    content="",        # EMPTY again — still not answering, needs one more tool
    tool_calls=[
        {
            "id": "call_def456",
            "name": "calculator",
            "args": {
                "expression": "1200 * 0.15"
            }
        }
    ]
)
```

Messages bag after iteration 2:

```text
1. SystemMessage   ("You are a helpful AI...")
2. HumanMessage    ("What is the price of 'Laptop Pro'...")
3. AIMessage       (content="", tool_calls=[database_query])
4. ToolMessage     (content="Results: [{'price': 1200.00}]", id="call_abc123")
5. AIMessage       (content="", tool_calls=[calculator]) ← NEW
iterations = 2
```

`should_continue` sees `tool_calls` is not empty → returns `"tools"`. Train goes to "tools" again.

---

### ToolNode runs — Tool Call 2 executes

```python
calculator(expression="1200 * 0.15")
# returns: "180.0"
```

**ToolMessage shape — Result of Tool Call 2:**

```python
ToolMessage(
    content="180.0",
    tool_call_id="call_def456",   # matches id from the second AIMessage
    name="calculator"
)
```

Messages bag after Tool Call 2:

```text
1. SystemMessage   ("You are a helpful AI...")
2. HumanMessage    ("What is the price of 'Laptop Pro'...")
3. AIMessage       (content="", tool_calls=[database_query])
4. ToolMessage     (content="Results: [{'price': 1200.00}]", id="call_abc123")
5. AIMessage       (content="", tool_calls=[calculator])
6. ToolMessage     (content="180.0", id="call_def456") ← NEW
iterations = 2
```

---

### Loop iteration 3 — agent\_node runs for the last time

LLM reads all 6 messages. It has both answers. It is ready to reply.

**AIMessage shape — Final Answer:**

```python
AIMessage(
    content="The Laptop Pro is priced at $1,200.00. A 15% tax on that is $180.00, making the total $1,380.00.",
    tool_calls=[]    # EMPTY — no more tools needed
)
```

Messages bag after iteration 3:

```text
1. SystemMessage   ("You are a helpful AI...")
2. HumanMessage    ("What is the price of 'Laptop Pro'...")
3. AIMessage       (content="", tool_calls=[database_query])
4. ToolMessage     (content="Results: [{'price': 1200.00}]", id="call_abc123")
5. AIMessage       (content="", tool_calls=[calculator])
6. ToolMessage     (content="180.0", id="call_def456")
7. AIMessage       (content="The Laptop Pro is priced at $1,200.00...") ← NEW
iterations = 3
```

`should_continue` sees `tool_calls` is empty → returns `"end"`. Train stops.

`run()` scans backwards from message 7, finds the first `AIMessage` with content, returns it.

**Final answer returned:** `"The Laptop Pro is priced at $1,200.00. A 15% tax on that is $180.00, making the total $1,380.00."`

---

### The full flow as one diagram

```text
initial_state: messages=[System, Human], iterations=0
        │
        ▼
  ┌─────────────┐
  │   AGENT     │  LLM reads [System, Human]
  │  iter = 1   │  → wants database_query
  └──────┬──────┘
         │ AIMessage(content="", tool_calls=[database_query])
         │ should_continue → "tools"
         ▼
  ┌─────────────┐
  │    TOOLS    │  runs database_query("SELECT price...")
  │             │  → ToolMessage("1200.00", id="call_abc123")
  └──────┬──────┘
         │ always loops back
         ▼
  ┌─────────────┐
  │   AGENT     │  LLM reads [System, Human, AI(db_call), Tool(1200.00)]
  │  iter = 2   │  → wants calculator
  └──────┬──────┘
         │ AIMessage(content="", tool_calls=[calculator "1200 * 0.15"])
         │ should_continue → "tools"
         ▼
  ┌─────────────┐
  │    TOOLS    │  runs calculator("1200 * 0.15")
  │             │  → ToolMessage("180.0", id="call_def456")
  └──────┬──────┘
         │ always loops back
         ▼
  ┌─────────────┐
  │   AGENT     │  LLM reads all 6 messages, has both answers
  │  iter = 3   │  → ready to reply, no more tools
  └──────┬──────┘
         │ AIMessage(content="The Laptop Pro is $1,200. Tax $180. Total $1,380.")
         │ should_continue → "end" (tool_calls is empty)
         ▼
        END → return final answer to user
```

---

## The one line that makes the loop work

```python
workflow.add_edge("tools", "agent")
```

After every tool runs, the train **always** goes back to "agent". The LLM then reads the new tool result and decides again: do I need another tool? Or am I ready to answer?

Without this line, the agent could only ever call one tool, then stop. With this line, the agent can call as many tools as needed (up to `max_iterations`) before giving the final answer.
