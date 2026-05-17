# Hands-on Labs — Config Tuning (Tier 1–5)

> **Why these labs exist:** This is the AI-engineering interview answer. When asked "how would you tune this system?" the answer is a guided tour of these sweeps and their trade-offs.
>
> **How to run:** Each lab changes ONE value in `.env`, restarts the server, runs the same 3 questions, and records the result. You do not need to write any code.
>
> **Courier lens:** Each lab ends with a courier takeaway explaining the trade-off in plain language.

## Table of Contents
- [Setup — Common to all labs](#setup--common-to-all-labs)
- [Lab 1: Temperature Sweep](#lab-1-temperature-sweep)
- [Lab 2: System Prompt Sweep](#lab-2-system-prompt-sweep)
- [Lab 3: Model Swap](#lab-3-model-swap)
- [Lab 4: Max Tokens Sweep](#lab-4-max-tokens-sweep)
- [Lab 5: Tool-Selection Sweep](#lab-5-tool-selection-sweep)
- [Lab 6: Max Iterations Sweep](#lab-6-max-iterations-sweep)
- [Lab 7: Eval Thresholds](#lab-7-eval-thresholds)
- [Lab 8: LLM-as-Judge Evaluation](#lab-8-llm-as-judge-evaluation)

---

## Setup — Common to all labs

**Step 1 — make sure the server is running:**

```bash
cd repos/ai-agent && poetry run start
```

Open <http://localhost:8200/docs>. You should see the Swagger page.

**Step 2 — the 3 fixed test questions (same for every lab):**

You will use these exact 3 questions in every lab. They are fixed so results are comparable across labs.

| Label | Question to paste |
| --- | --- |
| Q1 | `What is sqrt(256) + 100?` |
| Q2 | `What are the top 3 most expensive products in the database?` |
| Q3 | `Search the web for latest AI news` |

**Step 3 — how to run each question:**

1. In Swagger, click **POST /v1/chat** → **Try it out**.
2. Paste the body (example for Q1):
   ```json
   {"message": "What is sqrt(256) + 100?"}
   ```
3. Click **Execute**.
4. In the response, note:
   - `tool_calls` — which tool did the agent call? (or empty if no tool)
   - `message` — the final answer text
   - `iterations` — how many times the agent looped
   - `latency_ms` — how long it took

**What "tool_calls correct" means for each question:**

| Question | Expected tool | Tool correct if |
| --- | --- | --- |
| Q1 (sqrt) | `calculator` | `tool_calls` contains `calculator` |
| Q2 (products) | `database_query` | `tool_calls` contains `database_query` |
| Q3 (AI news) | `web_search` | `tool_calls` contains `web_search` |

**Step 4 — how to restart after a config change:**

```bash
# stop the running server (Ctrl+C), then:
poetry run start
```

---

## Lab 1: Temperature Sweep

**What we change:** `LLM_TEMPERATURE` in `.env`

**What temperature controls:** How random the model's word choices are. Temperature 0.0 = always picks the most likely word. Temperature 1.0 = picks randomly. For tool-calling agents, low temperature is better — the model follows the tool schema precisely.

**Hypothesis:** At 0.0 the agent reliably picks the correct tool. At 0.7+ the model starts inventing tool argument names that do not exist in the schema.

---

### Value 1 — Temperature 0.0

**Step 1 — set the config:**

Open `.env` and change:

```bash
LLM_TEMPERATURE=0.0
```

Restart the server.

**Step 2 — run Q1 (calculator):**

Paste in Swagger POST /v1/chat:

```json
{"message": "What is sqrt(256) + 100?"}
```

Click **Execute**. Expected: `tool_calls` contains `calculator`, answer is `116.0`.

**Step 3 — run Q2 (database):**

```json
{"message": "What are the top 3 most expensive products in the database?"}
```

Click **Execute**. Expected: `tool_calls` contains `database_query`, response lists 3 products.

**Step 4 — run Q3 (web search):**

```json
{"message": "Search the web for latest AI news"}
```

Click **Execute**. Expected: `tool_calls` contains `web_search`.

**Step 5 — record results for temperature 0.0:**

| Question | Tool correct? (yes/no) | Answer looks right? | `iterations` | `latency_ms` |
| --- | --- | --- | --- | --- |
| Q1 sqrt | | | | |
| Q2 products | | | | |
| Q3 AI news | | | | |

---

### Value 2 — Temperature 0.3 (default)

**Step 1 — set the config:**

```bash
LLM_TEMPERATURE=0.3
```

Restart the server. Run the same 3 questions and record results.

| Question | Tool correct? (yes/no) | Answer looks right? | `iterations` | `latency_ms` |
| --- | --- | --- | --- | --- |
| Q1 sqrt | | | | |
| Q2 products | | | | |
| Q3 AI news | | | | |

---

### Value 3 — Temperature 0.7

**Step 1 — set the config:**

```bash
LLM_TEMPERATURE=0.7
```

Restart the server. Run the same 3 questions and record results.

At this value you may see the model invent tool argument names — the call fails and the agent loops again or gives up.

| Question | Tool correct? (yes/no) | Answer looks right? | `iterations` | `latency_ms` |
| --- | --- | --- | --- | --- |
| Q1 sqrt | | | | |
| Q2 products | | | | |
| Q3 AI news | | | | |

---

### What we learned

Low temperature is essential for tool-using agents. High temperature causes the model to invent parameter names that are not in the tool schema — the call fails, burns a loop iteration, and the agent often gives up.

### 🚚 Courier takeaway

A precise courier follows the shipping manifest exactly. A creative courier invents a pickup locker that does not exist and the parcel never arrives.

---

## Lab 2: System Prompt Sweep

**What we change:** `SYSTEM_PROMPT` in `src/agent/graph.py`

**What the system prompt controls:** The first message the model sees on every request. It sets the rules — whether to use tools or answer from memory.

**Hypothesis:** A strict prompt ("always use a tool for data questions, never guess") forces correct tool use. A lax prompt lets the model skip the tool and answer from memory.

---

### Value 1 — Strict prompt

**Step 1 — set the config:**

Open `src/agent/graph.py`. Find `SYSTEM_PROMPT` and replace it with:

```python
SYSTEM_PROMPT = """You are a helpful AI assistant with access to tools.
RULES — follow these exactly:
1. For any math or calculation question, you MUST use the calculator tool. Never calculate in your head.
2. For any question about products, prices, or database records, you MUST use the database_query tool.
3. For any question about current news, events, or web content, you MUST use the web_search tool.
4. Only answer directly if the question needs none of the above tools.
Never skip a tool when one applies."""
```

Restart the server.

**Step 2 — run Q1 (calculator):**

```json
{"message": "What is sqrt(256) + 100?"}
```

Expected: `tool_calls` contains `calculator`. Strict prompt should force this reliably.

**Step 3 — run Q2 (database):**

```json
{"message": "What are the top 3 most expensive products in the database?"}
```

Expected: `tool_calls` contains `database_query`.

**Step 4 — run Q3 (web search):**

```json
{"message": "Search the web for latest AI news"}
```

Expected: `tool_calls` contains `web_search`.

**Step 5 — record results for strict prompt:**

| Question | Tool correct? (yes/no) | Answer looks right? | `iterations` |
| --- | --- | --- | --- |
| Q1 sqrt | | | |
| Q2 products | | | |
| Q3 AI news | | | |

---

### Value 2 — Balanced prompt (default)

**Step 1 — restore the original prompt in `src/agent/graph.py`:**

```python
SYSTEM_PROMPT = """You are a helpful AI assistant with access to tools. You can:
1. Search the web for current information
2. Perform mathematical calculations
3. Query a product database with SQL

When answering questions:
- Use tools ONLY when the user explicitly asks for a calculation, database query, or web search
- For greetings, introductions, or personal statements, respond directly — do NOT call any tool
- Be concise and accurate

If you don't need a tool, just respond directly."""
```

Restart. Run the same 3 questions and record.

| Question | Tool correct? (yes/no) | Answer looks right? | `iterations` |
| --- | --- | --- | --- |
| Q1 sqrt | | | |
| Q2 products | | | |
| Q3 AI news | | | |

---

### Value 3 — Lax prompt

**Step 1 — set this prompt:**

```python
SYSTEM_PROMPT = """You are a helpful AI assistant. Answer questions helpfully.
Use tools if you want to, but feel free to answer from your own knowledge if you know the answer."""
```

Restart. Run the same 3 questions. At this setting the model will often skip tools and answer from memory — the database answer will be invented.

| Question | Tool correct? (yes/no) | Answer looks right? | `iterations` |
| --- | --- | --- | --- |
| Q1 sqrt | | | |
| Q2 products | | | |
| Q3 AI news | | | |

**After this lab, restore the balanced prompt** (Value 2 above) before continuing.

---

### What we learned

The system prompt is the single biggest quality lever. A lax prompt lets the model skip the tool entirely and invent an answer that sounds plausible but is wrong (hallucination). Always test the system prompt by checking `tool_calls` is not empty on tool-requiring questions.

### 🚚 Courier takeaway

A strict shipping manifest says "use the calculator depot for all arithmetic". A lax one says "feel free to estimate" — and the courier does, and gets it wrong.

---

## Lab 3: Model Swap

**What we change:** `OLLAMA_CHAT_MODEL` in `.env`

**What it controls:** Which underlying language model runs the agent. Larger models follow tool schemas better. Small models invent JSON.

**Hypothesis:** `llama3.2` (3B) works for simple questions. For complex multi-tool questions it may invent tool arguments. Larger models handle both reliably.

---

### Value 1 — llama3.2 (3B, default)

**Step 1 — confirm current config:**

```bash
OLLAMA_CHAT_MODEL=llama3.2
```

Restart the server (or it may already be running this).

**Step 2 — run Q1:**

```json
{"message": "What is sqrt(256) + 100?"}
```

Expected: `tool_calls` contains `calculator`, answer is `116.0`.

**Step 3 — run Q2:**

```json
{"message": "What are the top 3 most expensive products in the database?"}
```

Expected: `tool_calls` contains `database_query`.

**Step 4 — run Q3:**

```json
{"message": "Search the web for latest AI news"}
```

Expected: `tool_calls` contains `web_search`.

**Step 5 — record results:**

| Question | Tool correct? (yes/no) | Answer looks right? | `latency_ms` |
| --- | --- | --- | --- |
| Q1 sqrt | | | |
| Q2 products | | | |
| Q3 AI news | | | |

---

### Value 2 — nomic-embed-text (embedding model — not a chat model)

> **Note:** This is intentionally a wrong model choice to show what happens.

**Step 1 — set the config:**

```bash
OLLAMA_CHAT_MODEL=nomic-embed-text
```

Restart. Run Q1:

```json
{"message": "What is sqrt(256) + 100?"}
```

Expected: the server returns an error or garbled output — embedding models cannot do chat or tool-calling.

**Record what happens:**

| What you saw | Error message (copy it here) |
| --- | --- |
| | |

**After this step, restore `OLLAMA_CHAT_MODEL=llama3.2`.**

---

### What we learned

Tool-calling is a trained skill, not a general LLM feature. Embedding models (like `nomic-embed-text`) produce vectors, not chat responses. For agents you need a chat + function-calling model. Small chat models (3B) work but can fail on complex tool schemas — they invent argument names that are not in the schema.

### 🚚 Courier takeaway

Different couriers have different training. A cargo loader (embedding model) cannot drive the delivery van. A small van stalls on a four-tool route — bring in the freight truck for heavy loads.

---

## Lab 4: Max Tokens Sweep

**What we change:** `LLM_MAX_TOKENS` in `.env`

**What it controls:** The maximum number of words (tokens) the model can output in one response. If a tool call JSON is longer than this limit, it gets cut off mid-way — and a cut-off JSON fails validation.

**Hypothesis:** At 256 tokens, complex tool-call arguments get truncated and fail. At 2048 (default) everything works. At 4096 there is no difference — you are paying for unused capacity.

---

### Value 1 — 256 tokens (too small)

**Step 1 — set the config:**

```bash
LLM_MAX_TOKENS=256
```

Restart the server.

**Step 2 — run Q2 (most likely to truncate — SQL query can be long):**

```json
{"message": "What are the top 3 most expensive products in the database?"}
```

Expected at this setting: you may see an incomplete response or an error like `unexpected end of JSON`. The `tool_calls` array may be empty even though the agent tried.

Record what you see:

| What happened | `tool_calls` value | `message` value |
| --- | --- | --- |
| | | |

**Step 3 — run Q1:**

```json
{"message": "What is sqrt(256) + 100?"}
```

Q1 has a short tool call so it may still work at 256 tokens.

| What happened | `tool_calls` value | `message` value |
| --- | --- | --- |
| | | |

---

### Value 2 — 2048 tokens (default)

**Step 1 — set the config:**

```bash
LLM_MAX_TOKENS=2048
```

Restart. Run all 3 questions and confirm everything works again.

| Question | Tool correct? (yes/no) | Answer looks right? |
| --- | --- | --- |
| Q1 sqrt | | |
| Q2 products | | |
| Q3 AI news | | |

---

### Value 3 — 4096 tokens

**Step 1 — set the config:**

```bash
LLM_MAX_TOKENS=4096
```

Restart. Run all 3 questions. You should see identical results to 2048 — no improvement because none of the answers need more than ~500 tokens.

| Question | Tool correct? (yes/no) | `latency_ms` difference vs 2048? |
| --- | --- | --- |
| Q1 sqrt | | |
| Q2 products | | |
| Q3 AI news | | |

**After this lab, restore `LLM_MAX_TOKENS=2048`.**

---

### What we learned

Set max tokens at least 4× your longest expected tool-call payload. Too low truncates the JSON and wastes a loop iteration. Too high costs extra tokens on every call for no benefit.

### 🚚 Courier takeaway

A tight parcel weight limit truncates the tool call mid-way and the depot rejects it. An oversized allowance pays for empty capacity on every trip.

---

## Lab 5: Tool-Selection Sweep

**What we change:** `TOOL_*_ENABLED` flags in `.env`

**What it controls:** Which tools the agent can see. If a tool is disabled, it is removed from the schema the LLM receives — the agent does not even know it exists.

**Hypothesis:** With only 1 tool enabled, the agent forces every question through that tool (even when wrong). With 3 tools it picks correctly. With 0 tools it hallucinates answers from memory.

---

### Value 1 — only calculator enabled

**Step 1 — set the config:**

```bash
TOOL_CALCULATOR_ENABLED=true
TOOL_DATABASE_QUERY_ENABLED=false
TOOL_WEB_SEARCH_ENABLED=false
```

Restart the server.

**Step 2 — run Q1 (should work — calculator is correct tool):**

```json
{"message": "What is sqrt(256) + 100?"}
```

Expected: `tool_calls` contains `calculator`, answer is `116.0`. ✅

**Step 3 — run Q2 (database query — but database tool is OFF):**

```json
{"message": "What are the top 3 most expensive products in the database?"}
```

Expected: the agent has no `database_query` tool so it either calls `calculator` (wrong tool, wrong result) or answers from memory (hallucinated product names).

Record what you see in `tool_calls` and `message`:

| `tool_calls` value | `message` (was the answer real or invented?) |
| --- | --- |
| | |

**Step 4 — run Q3 (web search — but web search tool is OFF):**

```json
{"message": "Search the web for latest AI news"}
```

Expected: agent has no `web_search` so it answers from memory (stale or invented news).

---

### Value 2 — all 3 tools enabled (correct config)

**Step 1 — set the config:**

```bash
TOOL_CALCULATOR_ENABLED=true
TOOL_DATABASE_QUERY_ENABLED=true
TOOL_WEB_SEARCH_ENABLED=true
```

Restart. Run all 3 questions and confirm each uses the correct tool.

| Question | Tool used | Tool correct? |
| --- | --- | --- |
| Q1 sqrt | | |
| Q2 products | | |
| Q3 AI news | | |

---

### What we learned

The tool registry is the security boundary. Disabling a tool does not make the agent safe — it makes it hallucinate instead of using the tool. Principle of least privilege applies, but you must also accept that the agent will answer from memory for any disabled tool.

### 🚚 Courier takeaway

One tool means the courier forces every job to fit that tool. Three tools means the right tool gets used for the right job. Zero tools means the courier guesses.

---

## Lab 6: Max Iterations Sweep

**What we change:** `AGENT_MAX_ITERATIONS` in `.env`

**What it controls:** How many times the agent can loop (think → call tool → observe result → think again) before it must give a final answer.

**Hypothesis:** At 1 iteration, multi-tool questions always fail — the agent calls the first tool and must stop before using the result. At 10 (default) everything works. At 25 there is no benefit.

---

### Value 1 — 1 iteration (too low)

**Step 1 — set the config:**

```bash
AGENT_MAX_ITERATIONS=1
```

Restart the server.

**Step 2 — run Q2 (needs database_query, then format the result — 2 loop steps):**

```json
{"message": "What are the top 3 most expensive products in the database?"}
```

Expected at 1 iteration: agent calls `database_query` then stops immediately — it never formats the result. The `message` may be empty or cut off. `iterations` = 1.

Record:

| `iterations` | `tool_calls` | `message` (complete answer or cut off?) |
| --- | --- | --- |
| | | |

**Step 3 — run Q1 (only needs 1 tool call — may still work):**

```json
{"message": "What is sqrt(256) + 100?"}
```

Record:

| `iterations` | `tool_calls` | Answer correct? |
| --- | --- | --- |
| | | |

---

### Value 2 — 10 iterations (default)

**Step 1 — set the config:**

```bash
AGENT_MAX_ITERATIONS=10
```

Restart. Run all 3 questions.

| Question | `iterations` | Tool correct? | Answer complete? |
| --- | --- | --- | --- |
| Q1 sqrt | | | |
| Q2 products | | | |
| Q3 AI news | | | |

---

### Value 3 — 25 iterations

**Step 1 — set the config:**

```bash
AGENT_MAX_ITERATIONS=25
```

Restart. Run all 3 questions. Results should be identical to 10 — none of these questions need more than 3 iterations. The higher limit only matters if a bug causes the agent to loop indefinitely (which now costs more tokens).

| Question | `iterations` | Same result as 10? |
| --- | --- | --- |
| Q1 sqrt | | |
| Q2 products | | |
| Q3 AI news | | |

**After this lab, restore `AGENT_MAX_ITERATIONS=10`.**

---

### What we learned

Cap iterations to the 95th percentile of successful trace lengths. High enough to finish real tasks. Low enough that a stuck agent gets killed before burning tokens. For this agent, 10 is enough for all 3 test questions.

### 🚚 Courier takeaway

A short dispatch limit makes the courier give up before finishing the route. A long limit lets them circle the same block twenty times. Ten stops is enough for any real delivery.

---

## Lab 7: Eval Thresholds

**What we change:** `EVAL_FAITHFULNESS_THRESHOLD` and `EVAL_KEYWORD_OVERLAP_PCT` in `.env`

**What it controls:** How strict the automatic pass/fail is when the `/v1/evaluate` endpoint scores a response. The same agent answer can pass or fail depending on the threshold.

**Hypothesis:** Strict thresholds (0.8+) expose silent tool-bypass where the agent answered from memory and got lucky. Lax thresholds (0.3) let those slide through as passing.

---

### Value 1 — strict thresholds

**Step 1 — set the config:**

```bash
EVAL_FAITHFULNESS_THRESHOLD=0.8
EVAL_KEYWORD_OVERLAP_PCT=0.7
```

Restart the server.

**Step 2 — get an agent answer for Q2 first:**

```json
{"message": "What are the top 3 most expensive products in the database?"}
```

Copy the full `message` value from the response.

**Step 3 — evaluate that answer:**

Click **POST /v1/evaluate** → **Try it out**. Paste (replace `PASTE_AGENT_ANSWER_HERE`):

```json
{
  "question": "What are the top 3 most expensive products in the database?",
  "answer": "PASTE_AGENT_ANSWER_HERE",
  "context": "Products retrieved from database using database_query tool"
}
```

Click **Execute**. Record `faithfulness_score` and `passed` from the response.

| Threshold setting | `faithfulness_score` | `passed` |
| --- | --- | --- |
| strict (0.8/0.7) | | |

---

### Value 2 — default thresholds

**Step 1 — set the config:**

```bash
EVAL_FAITHFULNESS_THRESHOLD=0.5
EVAL_KEYWORD_OVERLAP_PCT=0.5
```

Restart. Run the same evaluate call with the same answer. Record result.

| Threshold setting | `faithfulness_score` | `passed` |
| --- | --- | --- |
| default (0.5/0.5) | | |

---

### Value 3 — lax thresholds

**Step 1 — set the config:**

```bash
EVAL_FAITHFULNESS_THRESHOLD=0.3
EVAL_KEYWORD_OVERLAP_PCT=0.3
```

Restart. Run the same evaluate call. At lax thresholds almost everything passes.

| Threshold setting | `faithfulness_score` | `passed` |
| --- | --- | --- |
| lax (0.3/0.3) | | |

**After this lab, restore defaults:**

```bash
EVAL_FAITHFULNESS_THRESHOLD=0.5
EVAL_KEYWORD_OVERLAP_PCT=0.5
```

---

### What we learned

Strict thresholds catch the day the agent answered from memory and got lucky. Lax thresholds let it pass. For production, set thresholds based on business risk — a medical assistant needs strict; a product recommendation can be looser.

### 🚚 Courier takeaway

The report card itself can be lenient or strict. The courier made the same delivery, but a strict auditor catches the day they skipped the depot and guessed the parcel contents.

---

## Lab 8: LLM-as-Judge Evaluation

**What we change:** `EVAL_MODE` in `.env`

**What it controls:** Whether evaluation uses Python rules (fast, free, deterministic) or a second LLM call (slower, costs a little, semantic).

**Hypothesis:** Rule-based eval checks keywords and sentence overlap. It cannot tell if the agent used the wrong tool but got a lucky answer. LLM-as-judge catches that by scoring tool-selection correctness separately.

---

### Value 1 — rule-based eval

**Step 1 — set the config:**

```bash
EVAL_MODE=rule_based
```

Restart the server.

**Step 2 — get an agent answer for Q1:**

```json
{"message": "What is sqrt(256) + 100?"}
```

Copy the `message` value.

**Step 3 — evaluate it:**

Click **POST /v1/evaluate** → **Try it out**. Paste:

```json
{
  "question": "What is sqrt(256) + 100?",
  "answer": "PASTE_AGENT_ANSWER_HERE",
  "context": "Calculator tool returned: sqrt(256) = 16.0, 16.0 + 100 = 116.0"
}
```

Click **Execute**. Record `faithfulness_score`, `keyword_overlap`, `passed`.

| Metric | Value |
| --- | --- |
| `faithfulness_score` | |
| `keyword_overlap` | |
| `passed` | |
| Time taken | |

**Step 4 — get an agent answer for Q2 and evaluate the same way:**

```json
{"message": "What are the top 3 most expensive products in the database?"}
```

Evaluate with context `"Products retrieved from database_query tool"`. Record result.

---

### Value 2 — LLM-as-judge

**Step 1 — set the config:**

```bash
EVAL_MODE=llm_judge
JUDGE_LLM_PROVIDER=ollama
JUDGE_LLM_MODEL=llama3.2
```

Restart the server.

**Step 2 — run the same evaluate call as Step 3 above** (Q1 with the same answer and context).

Click **Execute**. Record the judge scores.

| Metric | Value |
| --- | --- |
| `faithfulness_score` | |
| `tool_selection_score` (if present) | |
| `passed` | |
| Time taken (should be ~500–2000ms longer) | |

**Step 3 — compare the two modes:**

| Mode | Q1 faithfulness | Q1 passed | Time |
| --- | --- | --- | --- |
| `rule_based` | | | |
| `llm_judge` | | | |

**After this lab, restore `EVAL_MODE=rule_based`.**

---

### When to use each mode

| Situation | Use this mode |
| --- | --- |
| Every single request in production | `rule_based` — free and instant |
| Nightly batch over 100 sample questions | `llm_judge` — catches tool-selection errors |
| Flagged requests (tool_calls was empty but should not be) | `llm_judge` — semantic check |
| 100% of all traffic | Never use `llm_judge` — cost adds up fast |

---

### What we learned

Rule-based eval is the right default. LLM-as-judge is uniquely useful for agents because it can score whether the agent chose the right tool — something keyword overlap cannot catch. Run it on samples, not every request.

### 🚚 Courier takeaway

Rule-based eval is a clipboard the dispatcher checks on every delivery. LLM-as-judge is the senior auditor who watches the courier choose their route — and notices the day they skipped the depot, guessed the parcel contents from memory, and got lucky. The clipboard says "delivered". The auditor says "but you took the wrong path".
