# How to Read the Hands-On Labs

> **Read this BEFORE opening Phase 1 or any config-tuning lab.** It explains the lab structure, what each phase covers, and how to run them — so the labs make sense from the first command rather than feeling like disconnected experiments.

---

## Table of Contents

- [Lab structure overview](#lab-structure-overview)
- [Prerequisites](#prerequisites)
- [How to run the labs](#how-to-run-the-labs)
- [What each lab covers](#what-each-lab-covers)
- [The shared yardstick](#the-shared-yardstick)
- [Suggested study order](#suggested-study-order)
- [What NOT to do](#what-not-to-do)

---

## Lab structure overview

The agent labs are **NOT one lab per feature**. They are **one lab per capability layer**, all building on a running agent. Each lab gives you a curl command (or short script), a set of observations to make, and a question to answer before moving to the next.

```
hands-on-labs/
├── hands-on-labs-phase-1.md        # Core agent: chat, tool calls, conversation continuity
├── hands-on-labs-phase-2.md        # Multi-turn reasoning, complex tool chaining, streaming
└── hands-on-labs-config-tuning.md  # Knob-turning: provider swap, tool enable/disable, model params
```

Phase 1 teaches you the baseline. Phase 2 pushes harder. Config Tuning is a reference you return to when you want to explore a specific dial.

> 🚚 **Courier way:** Phase 1 is your first shift — learn the route, meet the specialists, make a delivery. Phase 2 is a complex multi-stop job. Config Tuning is the shift manager's handbook of dials to adjust when something about the delivery isn't working.

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.12 | Required by the project |
| Poetry | 1.8+ | Dependency management: `pip install poetry` |
| Ollama | Any recent | Only needed for local mode: `brew install ollama` / download from ollama.com |
| A pulled Ollama model | e.g. `llama3.2` | Run `ollama pull llama3.2` before starting labs |
| `curl` or an HTTP client | Any | All labs use `curl` examples |

Cloud provider credentials (AWS, Azure) are **not** needed for local labs — all Phase 1 and Phase 2 labs run against a local Ollama instance at no cost.

---

## How to run the labs

### 1. Start Ollama (local mode)

```bash
ollama serve           # If not already running as a daemon
ollama pull llama3.2   # If you haven't pulled a model yet
```

### 2. Start the agent

Option A — Docker Compose (simplest):

```bash
docker compose up -d
curl http://localhost:8200/health   # Should return {"status": "healthy"}
```

Option B — Local Python:

```bash
poetry install
poetry run uvicorn src.main:app --reload --port 8200
curl http://localhost:8200/health
```

### 3. Open the lab file and follow the steps

Each lab is self-contained: it explains what to do, provides the exact commands, and tells you what to observe. You do not need to read them in order for Phase 1, but Phase 2 assumes you have completed Phase 1 first.

---

## What each lab covers

### Phase 1 — Agent Foundation (~2 hours)

| Lab | What you do | What you learn |
|-----|-------------|----------------|
| Lab 1: First Agent Interaction | Send a simple message to `POST /v1/chat` | How the agent responds, what `tool_calls_made` looks like when no tools are used |
| Lab 2: Tool Exploration | Ask questions that trigger tool calls (calculator, web search) | How the LangGraph loop decides when to call a specialist; what the tool call list looks like |
| Lab 3: Conversation Continuity | Send follow-up messages using `conversation_id` | How conversation history is persisted in SQLite; how context is carried across turns |
| Lab 4: Health Check and Monitoring | Query `GET /health` and `GET /v1/tools` | What the four health components mean; what tools are registered |

### Phase 2 — Multi-Turn and Streaming (~2 hours)

| Lab | What you do | What you learn |
|-----|-------------|----------------|
| Lab 1: Complex Tool Chaining | Ask a question that requires multiple tool calls in sequence | How the ReAct loop iterates; how intermediate tool results feed back into the next LLM step |
| Lab 2: Streaming Response | Use `POST /v1/chat/stream` instead of `POST /v1/chat` | How the SSE stream delivers events; why this is simulated streaming (step-by-step, not token-by-token) |
| Lab 3: Conversation Management | List, retrieve, and delete conversations via the `/v1/conversations` endpoints | The full CRUD lifecycle of a conversation; when to clean up |

### Config Tuning — Reference Labs

| Lab | Knob | What you explore |
|-----|------|-----------------|
| CT-1: Model swap | `CLOUD_PROVIDER` + model config | Switching from Ollama to AWS Bedrock or Azure OpenAI; latency and cost differences |
| CT-2: Tool enable/disable | `TOOL_*_ENABLED` env vars | Removing tools from the registry; agent behaviour when a specialist is unavailable |
| CT-3: LangGraph parameters | `max_iterations`, `temperature` | How the loop depth cap affects complex queries; how temperature shifts response style |

---

## The shared yardstick

Unlike ai-gateway, there is no single five-metric dashboard. The agent is judged by three signals across every lab:

| Signal | Where to read it | What it tells you |
|--------|-----------------|-------------------|
| `tool_calls_made` | Response body | Which specialists the courier called, and in what order |
| `token_count` | Response body (estimated) | Rough size of the turn — useful for spotting unexpectedly long loops |
| `status` from `GET /health` | Health endpoint | Whether all four components are live before and after the lab |

There is no cost row, no cache hit rate, and no latency middleware. If you want latency numbers, time your `curl` calls manually or use a load-testing script.

---

## Suggested study order

| Step | Lab | Why |
|------|-----|-----|
| 1 | Phase 1 Lab 1 | Establish the baseline — one message, no tools, clean response |
| 2 | Phase 1 Lab 2 | First tool call — see the ReAct loop in action |
| 3 | Phase 1 Lab 3 | Add memory — multi-turn conversation over SQLite |
| 4 | Phase 1 Lab 4 | Inspect the health and tool endpoints — understand the agent's self-reported state |
| 5 | Phase 2 Lab 1 | Chain multiple tools in a single request |
| 6 | Phase 2 Lab 2 | Streaming — same agent, different delivery mechanism |
| 7 | Config Tuning | Return here when you want to explore a specific variable |

Config Tuning labs are reference material, not a linear sequence. Jump to CT-1 if you want to try a cloud provider; jump to CT-2 if you want to understand tool registration.

---

## What NOT to do

1. **Don't skip Phase 1 Lab 1.** The baseline response structure (`tool_calls_made`, `conversation_id`, `token_count`) appears in every subsequent lab. Without seeing it once cleanly, the later labs look confusing.
2. **Don't run Phase 2 before completing Phase 1.** Phase 2 assumes you understand the ReAct loop and conversation persistence. It does not re-explain them.
3. **Don't run labs without Ollama.** The local agent will start and pass the health check, but every chat request will fail with a provider connection error. Verify `ollama serve` is running first.
4. **Don't compare token counts across providers.** The `token_count` field is `chars // 4` — an estimate. It is consistent within a session but not comparable between Ollama and a cloud provider using real tokenisation.
5. **Don't leave the cloud deployed after finishing.** If you ran the Config Tuning labs against AWS or Azure, run `terraform destroy` to avoid unexpected charges. The €5 budget alarm is a warning, not a hard stop.
