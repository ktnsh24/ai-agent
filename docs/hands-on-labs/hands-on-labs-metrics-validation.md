# Hands-on Labs — Metrics Validation: From Bad to Good

> **Labs 9–13:** Prove the agent works by deliberately breaking it, measuring the bad metrics, fixing it, and showing the business a before/after table.
>
> **Time:** ~3 hours total

---

## Table of Contents

- [Why these labs exist](#why-these-labs-exist)
- [The 5 metrics you will measure](#the-5-metrics-you-will-measure)
- [The Courier Analogy — Understanding Validation Metrics](#-the-courier-analogy--understanding-validation-metrics)
- [Lab 9: The Broken Loop — max\_iterations=1](#lab-9-the-broken-loop--max_iterations1)
- [Lab 10: Tools Disabled — Hallucination Lab](#lab-10-tools-disabled--hallucination-lab)
- [Lab 11: Poisoned System Prompt — Tool Avoidance](#lab-11-poisoned-system-prompt--tool-avoidance)
- [Lab 12: No Conversation Memory — Context Lab](#lab-12-no-conversation-memory--context-lab)
- [Lab 13: LLM-as-Judge — The Final Quality Gate](#lab-13-llm-as-judge--the-final-quality-gate)
- [Business Dashboard — Summary Table](#business-dashboard--summary-table)

---

## Why these labs exist

When you finish building the agent, it feels like it works. But "feels like it works" is not good enough to show a business.

These labs do something different from the Phase 1 and Phase 2 labs. They do not teach you new features. Instead they answer one question:

> **"How do you prove, with numbers, that the agent is production-ready?"**

The method: break one thing at a time, measure the bad metric, fix it, measure again. The metric moving from bad to good is the proof.

---

## The 5 metrics you will measure

| Metric | What it measures | Bad number | Good number |
| --- | --- | --- | --- |
| **Tool selection accuracy** | For 10 test questions, how many times did the agent call the correct tool? | 40% | 95%+ |
| **Multi-tool completion rate** | For questions needing 2 tools, how often did the agent use both and finish? | 0% | 90%+ |
| **Answer correctness** | For questions with known answers, is the final answer right? | 30% | 95%+ |
| **Hallucination rate** | How often did the agent answer without calling a tool when it should have used one? | 60% | less than 5% |
| **Response latency p95** | Out of 100 requests, 95 are faster than this number | 30+ seconds | less than 5 seconds |

---

## 🚚 The Courier Analogy — Understanding Validation Metrics

| Metric | 🚚 Courier Analogy | What It Means for the Agent | How It's Calculated |
| --- | --- | --- | --- |
| **Tool selection accuracy** | Courier picks the right pickup locker — math questions go to the calculator depot, not the web depot | Agent calls the expected tool for each question type | Compare `tool_name` in response vs. expected tool for that query |
| **Multi-tool completion rate** | Courier completes a route with two stops without stopping after the first | Agent calls two tools in sequence and delivers a final answer | Check `tool_calls` length ≥ 2 AND `message` is not empty |
| **Answer correctness** | Parcel arrives at the right address, not a guess | Final answer matches the known correct answer | Compare agent answer to ground truth answer |
| **Hallucination rate** | Courier makes up a delivery address instead of checking the map | Agent guesses an answer it should have looked up | Count responses with no `tool_calls` when tool was required |
| **Response latency p95** | 95 out of 100 deliveries arrive within the promised time window | Agent completes 95% of requests faster than the target | `time_end − time_start`, sort, read the 95th value |

---

## Lab 9: The Broken Loop — max\_iterations=1

**🎯 What we measure:** Does limiting the agent loop to 1 iteration cause multi-tool queries to fail? After restoring the limit, does `multi_tool_completion_rate` rise above 90%?

> 🏢 **Business context:** The engineering team asks: "What happens if we set a low safety limit on the agent loop?" This lab shows that too tight a limit kills multi-step reasoning.

### How to run this lab

**Step 1 — break it:**

Open `.env` and set:

```bash
AGENT_MAX_ITERATIONS=1
```

Restart the server:

```bash
poetry run start
```

**Step 2 — run the 5 test questions:**

Use these exact questions so results are comparable across labs.

1. Open <http://localhost:8200/docs> in your browser.
2. Click **POST /v1/chat** → **Try it out**.

**Question 1 — needs database\_query + calculator (2 tools):**

1. Paste: `{"message": "What is the price of Laptop Pro and calculate 15% tax on it?"}`
2. Click **Execute** — record `tool_calls`, `iterations`, and `message`.

**Question 2 — needs database\_query + calculator (2 tools):**

1. Paste: `{"message": "Find the cheapest product and calculate a 20% discount on it"}`
2. Click **Execute** — record results.

**Question 3 — needs calculator only (1 tool):**

1. Paste: `{"message": "What is sqrt(256) + 100?"}`
2. Click **Execute**.

**Question 4 — needs database\_query only (1 tool):**

1. Paste: `{"message": "List all products in the database"}`
2. Click **Execute**.

**Question 5 — no tool needed:**

1. Paste: `{"message": "What is the capital of France?"}`
2. Click **Execute** — `tool_calls` should be empty, `iterations` = 1.

**Step 3 — fix it:**

```bash
# .env
AGENT_MAX_ITERATIONS=10
```

Restart and run the same 5 questions again.

### Expected result

| State | `multi_tool_completion_rate` | `answer_correctness` | `iterations` |
| --- | --- | --- | --- |
| **Broken** (`max_iterations=1`) | 0% | 25% | always 1 |
| **Fixed** (`max_iterations=10`) | 90%+ | 95%+ | 2.3 avg |

With `max_iterations=1`: Questions 1 and 2 always fail — agent calls the first tool then stops. Questions 3 and 5 may still pass (they need 0 or 1 tool).

### Pass / Fail criteria

- [ ] Broken state: Questions 1 and 2 return incomplete answers
- [ ] Broken state: All responses show `iterations: 1`
- [ ] Fixed state: Questions 1 and 2 return `tool_calls` with 2 entries
- [ ] Fixed state: `iterations` is greater than 1 for multi-tool questions

**Run with the script:**

```bash
.venv/bin/python scripts/run_all_labs.py --only 9
```

### What you learn (AI engineer)

`max_iterations` in `graph.py` controls how many times the agent can go around the loop. Each loop is: LLM decides → call tool → LLM decides → call tool (or stop). Set it too low and every multi-step question fails. Set it too high and a bug can cause infinite loops. The sweet spot for this agent is 10. In AWS Step Functions, `MaxConcurrency` on a Map state and per-state retry limits serve the same purpose — always set a maximum.

**✅ Skill unlocked:** You can read `iterations` in a response and know immediately whether the agent loop limit is the cause of a partial answer.

---

## Lab 10: Tools Disabled — Hallucination Lab

**🎯 What we measure:** With all tools disabled, does the `hallucination_rate` rise to ~95%? After re-enabling tools, does it fall below 5%?

> 🏢 **Business context:** Security asks: "What if we disable all tools — is the agent safe to use?" This lab shows that disabling tools makes the agent answer confidently from memory, which means wrong answers.

### How to run this lab

**Step 1 — break it:**

Open `.env` and set:

```bash
TOOL_CALCULATOR_ENABLED=false
TOOL_DATABASE_QUERY_ENABLED=false
TOOL_WEB_SEARCH_ENABLED=false
```

Restart the server.

**Step 2 — why this breaks things:**

`registry.py` reads these flags. If all are false, `get_all_tools()` returns an empty list. Then `graph.py` gives the LLM no tools to call. It answers everything from memory — including product prices it has never seen.

**Step 3 — run the same 5 questions:**

1. Open <http://localhost:8200/docs> in your browser.
2. Click **POST /v1/chat** → **Try it out**.

**Math question (agent must guess because calculator is off):**

1. Paste: `{"message": "What is sqrt(256) + 100?"}`
2. Click **Execute** — `tool_calls` should be empty. Note the answer — is it correct?

**Database + calculator question (agent will invent the price):**

1. Paste: `{"message": "What is the price of Laptop Pro and calculate 15% tax on it?"}`
2. Click **Execute** — `tool_calls` should be empty. Note the invented price.

A hallucinated answer looks like:

```text
"The Laptop Pro typically retails for around $800–$1,200.
A 15% tax would be approximately $120–$180."
```

The LLM guessed. It does not know your database.

**Step 4 — fix it:**

```bash
# .env
TOOL_CALCULATOR_ENABLED=true
TOOL_DATABASE_QUERY_ENABLED=true
TOOL_WEB_SEARCH_ENABLED=true
```

Restart and run the same questions again.

### Expected result

| State | `tool_selection_accuracy` | `answer_correctness` | `hallucination_rate` |
| --- | --- | --- | --- |
| **Broken** (tools off) | 0% | 15% | 95% |
| **Fixed** (tools on) | 92% | 95% | 4% |

### Pass / Fail criteria

- [ ] Broken state: `tool_calls` is empty on math and database questions
- [ ] Broken state: Price answers are round numbers or ranges — not your actual DB value
- [ ] Fixed state: `tool_calls` contains `calculator` and `database_query`
- [ ] Fixed state: Price matches the actual value returned by the database tool

**Run with the script:**

```bash
.venv/bin/python scripts/run_all_labs.py --only 10
```

### What you learn (AI engineer)

The tool registry is the security boundary of the agent. Without tools the LLM falls back to pattern-matching on its training data. Hallucination rate — responses with no `tool_calls` when a tool was required — is the clearest signal of a tool-access problem. In AWS IAM terms: the tool registry is a policy that grants `Allow` on specific actions. Enabling a tool = granting the permission. Disabling = revoking it. Principle of least privilege applies to both.

**✅ Skill unlocked:** You can identify hallucinations from the absence of `tool_calls` in a response that should have used a tool.

---

## Lab 11: Poisoned System Prompt — Tool Avoidance

**🎯 What we measure:** Does a system prompt that says "do not use tools" suppress `tool_calls` even when tools are enabled? After restoring the correct prompt, do tool calls reappear?

> 🏢 **Business context:** A developer asks: "Can we make the agent faster by telling it not to use tools?" This lab shows that a bad system prompt overrides even correctly configured tools.

### How to run this lab

**Step 1 — break it:**

Open `src/agent/graph.py`. Find the `SYSTEM_PROMPT` constant and change it to:

```python
SYSTEM_PROMPT = """You are a helpful assistant.
Answer all questions from your own knowledge.
Do not use any tools — answer directly every time."""
```

Restart the server.

**Step 2 — why this breaks things:**

The system prompt is the first message in every LLM request. When it says "do not use tools", the LLM ignores its tool schemas even though they are attached via `bind_tools`. The `should_continue` decision in `graph.py` routes to `"end"` immediately because `tool_calls` is always empty.

**Step 3 — run the same 5 questions:**

1. Open <http://localhost:8200/docs> in your browser.
2. Click **POST /v1/chat** → **Try it out**.
3. Paste: `{"message": "What is sqrt(256) + 100?"}`
4. Click **Execute** — record `iterations` and `tool_calls`.

You will see `iterations: 1` on every question. The loop never runs a second time.

**Step 4 — fix it:**

Restore the original `SYSTEM_PROMPT` in `graph.py`:

```python
SYSTEM_PROMPT = """You are a helpful AI assistant with access to tools. You can:
1. Search the web for current information
2. Perform mathematical calculations
3. Query a product database with SQL

When answering questions:
- Use tools when you need external information or calculations
- Be concise and accurate
- Show your work when doing calculations

If you don't need a tool, just respond directly."""
```

Restart and run the same questions again.

### Expected result

| State | `tool_selection_accuracy` | `hallucination_rate` | `iterations` avg |
| --- | --- | --- | --- |
| **Broken** (poisoned prompt) | 5% | 90% | 1 (always) |
| **Fixed** (correct prompt) | 92% | 4% | 2.3 |

### Pass / Fail criteria

- [ ] Broken state: `iterations` = 1 on every single question
- [ ] Broken state: `tool_calls` is empty even for math questions
- [ ] Fixed state: Math questions show `iterations > 1` and `tool_calls` contains `calculator`
- [ ] Fixed state: Direct questions (capital of France) still return `tool_calls: []`

**Run with the script:**

```bash
.venv/bin/python scripts/run_all_labs.py --only 11
```

### What you learn (AI engineer)

The system prompt is the most powerful single input to the agent. It controls behaviour at the LLM level, before any tool schema is evaluated. A bad prompt overrides even correctly configured tools. In Amazon Bedrock Agents, the equivalent is the "Instructions for the agent" field — a wrong instruction there causes the same tool-avoidance failure. Always test your system prompt explicitly says when to use tools, and verify by checking `iterations` is greater than 1 on tool-requiring questions.

**✅ Skill unlocked:** You can diagnose tool-avoidance failures from `iterations=1` on every request, even when tools are enabled.

---

## Lab 12: No Conversation Memory — Context Lab

**🎯 What we measure:** Does passing empty history on every request make turn-2 follow-up questions fail? After restoring history loading, does `follow_up_accuracy` rise above 85%?

> 🏢 **Business context:** The product team wants a two-turn conversation: "What is the price of Laptop Pro?" followed by "Now calculate 15% tax on that." Without memory, the second question fails because the agent has forgotten the price.

### How to run this lab

**Step 1 — break it:**

Open `src/routes/chat.py`. Find where `conversation_history` is passed to `agent_graph.run()` and change it to always pass an empty list:

```python
# BREAK: pass empty history always — agent forgets every turn
result = await agent_graph.run(
    user_message=message.message,
    conversation_history=[],   # was: loaded from conversation store
    max_iterations=settings.agent_max_iterations,
)
```

Restart the server.

**Step 2 — run a two-turn test:**

1. Open <http://localhost:8200/docs> in your browser.
2. Click **POST /v1/chat** → **Try it out**.

**Turn 1:**

1. Paste: `{"message": "What is the price of Laptop Pro?", "conversation_id": "test-123"}`
2. Click **Execute** — note the answer.

**Turn 2 (agent must remember turn 1):**

1. Paste: `{"message": "Now calculate 15% tax on that price.", "conversation_id": "test-123"}`
2. Click **Execute** — with memory broken, the agent says it does not know the price.

Expected broken output on turn 2:

```text
"I'm sorry, I don't know which price you are referring to.
 Could you please tell me the product name and price again?"
```

**Step 3 — fix it:**

Restore the original code in `chat.py`:

```python
conversation_history = await conversation_store.get_messages(conversation_id)

result = await agent_graph.run(
    user_message=message.message,
    conversation_history=conversation_history,
    max_iterations=settings.agent_max_iterations,
)
```

Restart and run the same two-turn test.

Expected fixed output on turn 2:

```text
"Based on the Laptop Pro price of $1,200.00 from our previous message,
 15% tax is $180.00, making the total $1,380.00."
```

### Expected result

| State | `follow_up_accuracy` | Turn 2 response |
| --- | --- | --- |
| **Broken** (no history) | 0% | "I don't know which price…" |
| **Fixed** (history loaded) | 85%+ | Correct answer using turn 1 data |

### Pass / Fail criteria

- [ ] Broken state: Turn 2 response asks for the product name again
- [ ] Fixed state: Turn 2 answer includes the price from turn 1 without being told again
- [ ] Fixed state: Using a different `conversation_id` on turn 2 still fails — correct behaviour

**Run with the script:**

```bash
.venv/bin/python scripts/run_all_labs.py --only 12
```

### What you learn (AI engineer)

The conversation store is what makes the agent feel like a real assistant. Without it, every message is a fresh start. The conversation ID links turns together — same as a session cookie in a web app. In production, SQLite (used here) cannot survive a container restart or scale to multiple pods. The right replacement is Amazon DynamoDB with `conversation_id` as the partition key and `timestamp` as the sort key. Same agent logic, durable storage.

**✅ Skill unlocked:** You can trace multi-turn failures to the conversation store and verify memory works by checking that turn 2 uses turn 1 data.

---

## Lab 13: LLM-as-Judge — The Final Quality Gate

**🎯 What we measure:** What is the average judge score (1–5) across all 5 test questions in the broken state vs the fixed state? Target: broken < 2.0, fixed ≥ 4.0.

> 🏢 **Business context:** The business asks for one number that summarises agent quality — not five separate metrics. The LLM-as-judge gives you that number. Run this lab last, after all fixes are in place.

### How to run this lab

This lab does not break anything. For each of the 5 questions below, you do two calls:

1. **Ask the agent** — paste the question, click Execute, copy `message` from the response.
2. **Ask the judge** — paste the judge body with that copied answer, click Execute, record the score (1–5).

Open <http://localhost:8200/docs> → **POST /v1/chat** → **Try it out** and keep this tab open for all steps.

---

**Question 1 — Step A: ask the agent**

Paste:

```json
{"message": "What is the price of Laptop Pro and calculate 15% tax on it?"}
```

Click **Execute**. Copy the `message` value from the response.

**Question 1 — Step B: ask the judge**

Replace `PASTE_AGENT_ANSWER_HERE` with what you just copied, then paste:

```json
{"message": "You are an evaluator. Score the following answer from 1 to 5. 5=fully correct. 4=mostly correct. 3=partially correct. 2=mostly wrong. 1=completely wrong or fabricated. Question: What is the price of Laptop Pro and calculate 15% tax on it? Expected: Price $1,200, tax $180, total $1,380. Agent answer: PASTE_AGENT_ANSWER_HERE. Reply with only a single number. No explanation."}
```

Click **Execute**. The `message` in the response is your score. Save it as `score1`.

---

**Question 2 — Step A: ask the agent**

Paste:

```json
{"message": "Find the cheapest product and calculate a 20% discount on it"}
```

Click **Execute**. Copy the `message` value from the response.

**Question 2 — Step B: ask the judge**

```json
{"message": "You are an evaluator. Score the following answer from 1 to 5. 5=fully correct. 4=mostly correct. 3=partially correct. 2=mostly wrong. 1=completely wrong or fabricated. Question: Find the cheapest product and calculate a 20% discount on it. Expected: product name, original price, and discounted price from the database. Agent answer: PASTE_AGENT_ANSWER_HERE. Reply with only a single number. No explanation."}
```

Click **Execute**. Save the score as `score2`.

---

**Question 3 — Step A: ask the agent**

Paste:

```json
{"message": "What is sqrt(256) + 100?"}
```

Click **Execute**. Copy the `message` value from the response.

**Question 3 — Step B: ask the judge**

```json
{"message": "You are an evaluator. Score the following answer from 1 to 5. 5=fully correct. 4=mostly correct. 3=partially correct. 2=mostly wrong. 1=completely wrong or fabricated. Question: What is sqrt(256) + 100? Expected: 116.0. Agent answer: PASTE_AGENT_ANSWER_HERE. Reply with only a single number. No explanation."}
```

Click **Execute**. Save the score as `score3`.

---

**Question 4 — Step A: ask the agent**

Paste:

```json
{"message": "List all products in the database"}
```

Click **Execute**. Copy the `message` value from the response.

**Question 4 — Step B: ask the judge**

```json
{"message": "You are an evaluator. Score the following answer from 1 to 5. 5=fully correct. 4=mostly correct. 3=partially correct. 2=mostly wrong. 1=completely wrong or fabricated. Question: List all products in the database. Expected: at least 3 products with names and prices returned from the database. Agent answer: PASTE_AGENT_ANSWER_HERE. Reply with only a single number. No explanation."}
```

Click **Execute**. Save the score as `score4`.

---

**Question 5 — Step A: ask the agent**

Paste:

```json
{"message": "What is the capital of France?"}
```

Click **Execute**. Copy the `message` value from the response.

**Question 5 — Step B: ask the judge**

```json
{"message": "You are an evaluator. Score the following answer from 1 to 5. 5=fully correct. 4=mostly correct. 3=partially correct. 2=mostly wrong. 1=completely wrong or fabricated. Question: What is the capital of France? Expected: Paris. Agent answer: PASTE_AGENT_ANSWER_HERE. Reply with only a single number. No explanation."}
```

Click **Execute**. Save the score as `score5`.

---

**Step 6 — record all scores**

| Question | Judge score (1–5) |
| --- | --- |
| What is the price of Laptop Pro and calculate 15% tax on it? | `score1` = |
| Find the cheapest product and calculate a 20% discount on it | `score2` = |
| What is sqrt(256) + 100? | `score3` = |
| List all products in the database | `score4` = |
| What is the capital of France? | `score5` = |

**Step 7 — calculate average**

```text
Average = (score1 + score2 + score3 + score4 + score5) / 5
```

Example: scores are 4, 5, 4, 3, 4 → Average = (4+5+4+3+4)/5 = **4.0**

### Expected result

| Lab config state | Average judge score |
| --- | --- |
| Lab 9 broken (`max_iterations=1`) | 1.4 / 5 |
| Lab 10 broken (tools disabled) | 1.2 / 5 |
| Lab 11 broken (poisoned prompt) | 1.1 / 5 |
| Lab 12 broken (no memory) | 2.0 / 5 |
| **All fixed** | **4.6 / 5** |

### Pass / Fail criteria

- [ ] Judge returns only a number (1–5), not a sentence
- [ ] Broken lab configs all score below 2.0
- [ ] All-fixed configuration scores 4.0 or above
- [ ] Score improves for each lab as you apply the fix

**Run with the script:**

```bash
.venv/bin/python scripts/run_all_labs.py --only 13
```

### What you learn (AI engineer)

LLM-as-judge gives you one number that captures overall agent quality. It is not perfect — the judge can also be wrong — but it scales far better than manual checking. A score above 4.0 on a representative question set is a reasonable production threshold. In MLOps this pattern is called model-based evaluation, or automated red-teaming. AWS Bedrock Model Evaluation supports the same thing at scale: run a judge model against a dataset of prompts and expected outputs, get accuracy, robustness, and toxicity scores automatically.

**✅ Skill unlocked:** You can run automated quality scoring and use a single number to communicate agent readiness to the business.

---

## Business Dashboard — Summary Table

After completing all 5 labs, you can show this table to the business.

| Lab | What was broken | Bad metric | Judge score before | Judge score after | Status |
| --- | --- | --- | --- | --- | --- |
| Lab 9 | Loop limit too low (`max_iterations=1`) | Multi-tool completion 0% | 1.4 / 5 | 4.6 / 5 | ✅ Fixed |
| Lab 10 | All tools disabled | Hallucination rate 95% | 1.2 / 5 | 4.6 / 5 | ✅ Fixed |
| Lab 11 | Prompt told agent not to use tools | Tool selection accuracy 5% | 1.1 / 5 | 4.6 / 5 | ✅ Fixed |
| Lab 12 | No conversation memory | Follow-up accuracy 0% | 2.0 / 5 | 4.6 / 5 | ✅ Fixed |
| Lab 13 | Final judge score (all fixes in place) | — | — | 4.6 / 5 | ✅ Production ready |

**Previous:** [Phase 2 Labs](hands-on-labs-phase-2.md)

### What you break — Lab 9

Open `.env` and set:

```bash
AGENT_MAX_ITERATIONS=1
```

Restart the server:

```bash
poetry run start
```

### Run the 10 test questions

Use these exact questions so results are comparable across labs. Save the responses.

1. Open <http://localhost:8200/docs> in your browser.
2. Click **POST /v1/chat** → **Try it out**.

**Question 1 — needs database\_query + calculator (2 tools):**

1. Paste:

   ```json
   {"message": "What is the price of Laptop Pro and calculate 15% tax on it?"}
   ```

2. Click **Execute** — record `tool_calls`, `iterations`, and `message`.

**Question 2 — needs database\_query + calculator (2 tools):**

1. Replace the body with:

   ```json
   {"message": "Find the cheapest product and calculate a 20% discount on it"}
   ```

2. Click **Execute** — record results.

**Question 3 — needs calculator only (1 tool):**

1. Replace the body with:

   ```json
   {"message": "What is sqrt(256) + 100?"}
   ```

2. Click **Execute** — record results.

**Question 4 — needs database\_query only (1 tool):**

1. Replace the body with:

   ```json
   {"message": "List all products in the database"}
   ```

2. Click **Execute** — record results.

**Question 5 — no tool needed (direct answer):**

1. Replace the body with:

   ```json
   {"message": "What is the capital of France?"}
   ```

2. Click **Execute** — `tool_calls` should be empty and `iterations` = 1.

### Expected bad metrics with max\_iterations=1

```text
Multi-tool completion rate:  0%   — agent calls first tool, hits limit, stops before second
Answer correctness:         25%   — only questions needing 0 or 1 tool can succeed
Hallucination rate:         60%   — agent gives partial or invented answer instead of looping
Iterations per request:      1    — always 1, never more
```

### The fix — Lab 9

```bash
# .env
AGENT_MAX_ITERATIONS=10
```

Restart and run the same 10 questions.

### Expected good metrics after fix — Lab 9

```text
Multi-tool completion rate:  90%
Answer correctness:          95%
Hallucination rate:           4%
Iterations per request:      2.3 average
```
