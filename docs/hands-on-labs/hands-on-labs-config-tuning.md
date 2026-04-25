# Hands-on Labs — Config Tuning (Tier 1–5)

> **Why these labs exist:** This is the AI-engineering interview answer. When asked "how would you tune this system?" the answer is a guided tour of these sweeps + their trade-offs.
>
> **How to run:** Each lab changes ONE config in `.env`, runs the same 3 questions, records the metrics, and explains the trade-off.
>
> **🫏 Donkey lens:** Each lab ends with a donkey takeaway summarising the trade-off in plain language.

## Table of Contents
- [Setup — Common to all labs](#setup--common-to-all-labs)
- [Lab 1: Temperature Sweep](#lab-1-temperature-sweep)
- [Lab 2: System Prompt Sweep](#lab-2-system-prompt-sweep)
- [Lab 3: Model Swap](#lab-3-model-swap)
- [Lab 4: Max Tokens Sweep](#lab-4-max-tokens-sweep)
- [Lab 5: Tool-Selection Sweep](#lab-5-tool-selection-sweep)
- [Lab 6: Max Iterations Sweep](#lab-6-max-iterations-sweep)
- [Lab 7: Eval Thresholds](#lab-7-eval-thresholds)

---

## Setup — Common to all labs

1. Make sure the API is running: `poetry run uvicorn src.main:app --port 8200 --reload`
2. Have the 3 fixed test questions ready (mix of tool-using cases):
   - **Q1:** "What is the weather in Amsterdam right now?" (web search tool)
   - **Q2:** "Calculate compound interest for €1000 at 5% over 10 years." (calculator tool)
   - **Q3:** "Query the conversations database for messages I sent yesterday." (database tool)
3. Each lab takes ~5–10 min: change config → restart API → run questions → record table

---

## Lab 1: Temperature Sweep — "How creative should the donkey be?"

**Config:** `LLM_TEMPERATURE` (default: `0.3`)
**What it controls:** Sampling randomness for the LLM.
**Hypothesis:** 0.0 = deterministic & faithful tool-use; higher = more hallucinated tool arguments.

### Setup
1. Set `LLM_TEMPERATURE=0.0` in `.env`
2. Run the same 3 questions (Q1–Q3)
3. Repeat for each value below

### Results table (fill in as you run)
| Value | Tool-call accuracy | Faithfulness | Latency (ms) | Cost (€) | Notes |
|---|---|---|---|---|---|
| 0.0 | ___ | ___ | ___ | ___ | ___ |
| 0.3 | ___ | ___ | ___ | ___ | ___ |
| 0.7 | ___ | ___ | ___ | ___ | ___ |

### What we learned
For tool-using agents, low temperature is essential — high temp invents tool names and parameter shapes, which then fail validation and burn loop iterations.

### 🫏 Donkey takeaway
Cold donkey reads the delivery note and uses the right tool; warm donkey invents a tool that doesn't exist on the wagon.

---

## Lab 2: System Prompt Sweep — "Strict vs lax delivery note"

**Config:** `SYSTEM_PROMPT` (default: balanced)
**What it controls:** The agent persona and tool-use rules prepended to every call.
**Hypothesis:** Strict prompt ("always cite the tool you used; never answer from memory if a tool is available") prevents bypassed tool-use.

### Setup
1. Set `SYSTEM_PROMPT` to the strict variant in `.env`
2. Run the same 3 questions (Q1–Q3)
3. Repeat for balanced and lax variants

### Results table (fill in as you run)
| Value | Tool-call accuracy | Faithfulness | Latency (ms) | Cost (€) | Notes |
|---|---|---|---|---|---|
| strict | ___ | ___ | ___ | ___ | ___ |
| balanced | ___ | ___ | ___ | ___ | ___ |
| lax | ___ | ___ | ___ | ___ | ___ |

### What we learned
The single biggest quality lever for agents — without an explicit "use tools, don't fabricate" rule, the LLM will skip tools whenever it thinks it knows the answer, which is almost always wrong for fresh data (weather, prices).

### 🫏 Donkey takeaway
A strict delivery note says "use the calculator on the wagon"; a lax note lets the donkey do mental arithmetic and get it wrong.

---

## Lab 3: Model Swap — "Which donkey is on duty?"

**Config:** `OLLAMA_CHAT_MODEL` / `AWS_BEDROCK_MODEL` / `AZURE_OPENAI_DEPLOYMENT_NAME` (default: `llama3.2`)
**What it controls:** The underlying LLM. Tool-calling quality varies wildly across models.
**Hypothesis:** Larger / instruction-tuned models follow the tool schema; small models hallucinate JSON.

### Setup
1. Set `CLOUD_PROVIDER=local` and `OLLAMA_CHAT_MODEL=llama3.2:1b`
2. Run the same 3 questions (Q1–Q3)
3. Repeat for each value below

### Results table (fill in as you run)
| Value | Tool-call accuracy | Faithfulness | Latency (ms) | Cost (€) | Notes |
|---|---|---|---|---|---|
| llama3.2:1b (local) | ___ | ___ | ___ | ___ | ___ |
| llama3.2 (3B, local) | ___ | ___ | ___ | ___ | ___ |
| Bedrock Haiku 4.5 | ___ | ___ | ___ | ___ | ___ |
| Azure GPT-4o | ___ | ___ | ___ | ___ | ___ |

### What we learned
Tool-calling is a skill — small open models can do RAG fine but mangle JSON tool schemas. For agents, prefer models with explicit tool-use training (Claude, GPT-4o, Llama-3.1-Instruct ≥8B).

### 🫏 Donkey takeaway
Different donkeys have different training; ask a pony to pull a 4-tool wagon and it stalls — bring in the bigger donkey for the heavy load.

---

## Lab 4: Max Tokens Sweep — "Cargo capacity of the reply"

**Config:** `LLM_MAX_TOKENS` (default: `2048`)
**What it controls:** Hard cap on output tokens per LLM call (each loop iteration).
**Hypothesis:** Too low = truncated tool args / answers; too high = inflated cost when tool calls are short.

### Setup
1. Set `LLM_MAX_TOKENS=256` in `.env`
2. Run the same 3 questions (Q1–Q3) and watch for truncated tool calls
3. Repeat for each value below

### Results table (fill in as you run)
| Value | Tool-call accuracy | Faithfulness | Latency (ms) | Cost (€) | Notes |
|---|---|---|---|---|---|
| 256 | ___ | ___ | ___ | ___ | ___ |
| 1024 | ___ | ___ | ___ | ___ | ___ |
| 2048 | ___ | ___ | ___ | ___ | ___ |
| 4096 | ___ | ___ | ___ | ___ | ___ |

### What we learned
Truncated JSON tool calls fail validation and waste a whole loop iteration. Set max_tokens at least 4× your worst-case tool-arg payload.

### 🫏 Donkey takeaway
A small cargo crate cuts the tool name in half and the wagon refuses it; an oversized crate pays for empty space on every trip.

---

## Lab 5: Tool-Selection Sweep — "Which tools are on the wagon today?"

**Config:** `TOOL_*_ENABLED` flags (`TOOL_WEB_SEARCH_ENABLED`, `TOOL_CALCULATOR_ENABLED`, `TOOL_DATABASE_QUERY_ENABLED`, plus any new tools)
**What it controls:** Which tools are exposed to the agent.
**Hypothesis:** With 1 tool the agent always picks it (even when wrong); with 3 tools it picks well; with 10+ tools it gets confused and picks the wrong one.

### Setup
1. **Subset A — 1 tool:** enable only `TOOL_WEB_SEARCH_ENABLED=true`
2. Run the same 3 questions (Q1–Q3) and note tool choices
3. **Subset B — 3 tools:** enable web search + calculator + database
4. **Subset C — 10 tools:** add 7 dummy tools (read_file, write_file, send_email, …) to push the prompt
5. Repeat with each subset

### Results table (fill in as you run)
| Value | Tool-call accuracy | Faithfulness | Latency (ms) | Cost (€) | Notes |
|---|---|---|---|---|---|
| 1 tool | ___ | ___ | ___ | ___ | ___ |
| 3 tools | ___ | ___ | ___ | ___ | ___ |
| 10 tools | ___ | ___ | ___ | ___ | ___ |

### What we learned
Tool selection accuracy follows an inverted-U: too few tools and the agent forces a square peg into a round hole, too many and the schema overflows attention. Curate the toolbox per agent role.

### 🫏 Donkey takeaway
A wagon with one tool means the donkey hammers everything; ten tools mean the donkey spends the day picking which to use; three is just right.

---

## Lab 6: Max Iterations Sweep — "How long can the agent loop?"

**Config:** `AGENT_MAX_ITERATIONS` (default: `10`)
**What it controls:** Hard cap on the agent's think → tool → observe loop before it must answer.
**Hypothesis:** Too low = unfinished tasks; too high = pointless circling and runaway cost.

### Setup
1. Set `AGENT_MAX_ITERATIONS=3` in `.env`
2. Run the same 3 questions (Q1–Q3) and note "max iterations exceeded" outcomes
3. Repeat for each value below

### Results table (fill in as you run)
| Value | Tool-call accuracy | Faithfulness | Latency (ms) | Cost (€) | Notes |
|---|---|---|---|---|---|
| 3 | ___ | ___ | ___ | ___ | ___ |
| 10 | ___ | ___ | ___ | ___ | ___ |
| 25 | ___ | ___ | ___ | ___ | ___ |

### What we learned
Cap iterations to the 95th-percentile of "successful" trace lengths — high enough to finish real tasks, low enough that a stuck agent gets killed before it burns tokens.

### 🫏 Donkey takeaway
A short leash makes the donkey give up before reaching the door; a long leash lets it wander the same corridor twenty times.

---

## Lab 7: Eval Thresholds — "How strict is the report card?"

**Config:** `EVAL_FAITHFULNESS_THRESHOLD` + `EVAL_KEYWORD_OVERLAP_PCT` (default: `0.5` / `0.5`)
**What it controls:** Pass/fail thresholds in the evaluator. Same answers, different verdicts.
**Hypothesis:** Strict thresholds expose silent tool-bypass (where the agent answered from memory and was lucky).

### Setup
1. Set `EVAL_FAITHFULNESS_THRESHOLD=0.8` and `EVAL_KEYWORD_OVERLAP_PCT=0.7`
2. Run Q1–Q3 and capture the report card
3. Repeat for default and lax presets

### Results table (fill in as you run)
| Value | Tool-call accuracy | Faithfulness | Latency (ms) | Cost (€) | Notes |
|---|---|---|---|---|---|
| strict (0.8/0.7) | ___ | ___ | ___ | ___ | ___ |
| default (0.5/0.5) | ___ | ___ | ___ | ___ | ___ |
| lax (0.3/0.3) | ___ | ___ | ___ | ___ | ___ |

### What we learned
For agents, also track "tool-call recall" — did the agent use the tool it should have? Lax thresholds let an unused-tool answer slip through if the answer happens to be right.

### 🫏 Donkey takeaway
The report card itself can be lenient or strict — the donkey did the same delivery, but a strict teacher catches the day it skipped the warehouse and guessed.
