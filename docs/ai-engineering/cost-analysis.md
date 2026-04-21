# Cost Analysis — AI Agent

> Per-service cost breakdown for AWS, Azure, and Local — including tool costs, conversation storage, and why we chose each service.

**Related:** [Architecture](../architecture-and-design/architecture.md) · [Tool Use Deep Dive](tool-use-deep-dive.md)

## Table of Contents

- [Monthly Cost Summary](#monthly-cost-summary)
  - [Development (personal account)](#development-personal-account)
  - [Production (small scale)](#production-small-scale-500-queriesdy)
- [Why Agents Cost More Than Chat](#why-agents-cost-more-than-chat)
- [Service-by-Service Breakdown](#service-by-service-breakdown)
  - [LLM Inference](#llm-inference)
  - [Web Search (Tavily)](#web-search-tavily)
  - [Calculator](#calculator)
  - [Database Query Tool](#database-query-tool)
  - [Conversation Store](#conversation-store)
- [What Alternatives Cost More](#what-alternatives-cost-more)
- [Decision Summary](#decision-summary)
- [How to Minimise Costs on Personal Account](#how-to-minimise-costs-on-personal-account)
- [Cost of Running Tests on Cloud](#cost-of-running-tests-on-cloud)
- [Budget Guard — Automatic Cost Protection](#budget-guard--automatic-cost-protection)

---

## Monthly Cost Summary

### Development (personal account)

| Service | AWS Cost/month | Azure Cost/month | Notes |
|---|---|---|---|
| LLM (pay-per-use) | ~$3–8 | ~$3–8 | Agents use more tokens (multi-turn reasoning) |
| Web Search (Tavily) | $0 (mock) | $0 (mock) | Mock fallback for development |
| Conversation Store | $0 (SQLite) | $0 (SQLite) | Local file-based storage |
| Container Hosting | $0 (local) | $0 (local) | Run locally |
| **Total** | **~$3–8/month** | **~$3–8/month** | Agent queries cost ~2× more tokens than simple chat |

### Production (small scale: ~500 queries/day)

| Service | AWS Cost/month | Azure Cost/month |
|---|---|---|
| LLM | ~$75–150 | ~$60–120 |
| Web Search (Tavily) | ~$5 (1000 searches/month) | ~$5 |
| Conversation Store | ~$5 (DynamoDB) | ~$5 (Cosmos DB) |
| Container Hosting | ~$30 (Fargate) | ~$20 (Container Apps) |
| **Total** | **~$115–190/month** | **~$90–150/month** |

> **Key insight:** Agents use 2–5× more tokens than simple chat because of the Think → Act → Observe loop. Each tool call adds ~200–500 tokens of reasoning.

---

## Why Agents Cost More Than Chat

### Token Multiplier Effect

A simple chat query: ~800 tokens (500 input + 300 output)

An agent query with 1 tool call:
```
Think (LLM call 1):    ~300 tokens   "I need to calculate this..."
Act (tool call):        ~0 tokens     calculator("sqrt(144)") — runs locally
Observe:                ~100 tokens   "The result is 12"
Respond (LLM call 2):  ~500 tokens   "The square root of 144 is 12."
─────────────────────────────────────
Total:                  ~900 tokens   (2 LLM calls)
```

An agent query with 3 tool calls:
```
Think → Act → Observe (×3): ~1800 tokens  (4 LLM calls)
Final response:             ~500 tokens
────────────────────────────────────────
Total:                      ~2300 tokens   (4 LLM calls)
```

| Query Type | LLM Calls | Tokens | AWS Cost | Azure Cost |
|---|---|---|---|---|
| Simple chat (no tools) | 1 | ~800 | $0.013 | $0.010 |
| 1 tool call | 2 | ~900 | $0.015 | $0.012 |
| 3 tool calls | 4 | ~2300 | $0.038 | $0.029 |
| Complex research (5+ tools) | 6+ | ~4000+ | $0.065+ | $0.050+ |

---

## Service-by-Service Breakdown

### LLM Inference

Same providers as V1 and V2 — the agent just uses more tokens per query:

| | AWS Bedrock (Claude 3.5 Sonnet) | Azure OpenAI (GPT-4o) | Local (Ollama) |
|---|---|---|---|
| **Input tokens** | $0.003/1K | $0.0025/1K | **$0** |
| **Output tokens** | $0.015/1K | $0.01/1K | **$0** |
| **Per simple query** | ~$0.013 | ~$0.010 | **$0** |
| **Per agent query (avg)** | ~$0.025 | ~$0.020 | **$0** |

### Web Search (Tavily)

| Option | Cost | Queries/month | Used when |
|---|---|---|---|
| **Mock (no API key)** | $0 | Unlimited | Development, testing |
| **Tavily Free** | $0 | 1000/month | Light usage |
| **Tavily Basic** | $5/month | 5000/month | Moderate usage |
| **Tavily Pro** | $50/month | 50,000/month | Production |

**What we chose:**
- **Development:** Mock search (returns pre-built results, no API key needed)
- **Production:** Tavily Basic ($5/month for 5000 searches)

### Calculator

| | Cost |
|---|---|
| Runs locally (AST-based Python) | **$0 always** |

No cloud service needed — the calculator is pure Python with no external dependencies.

### Database Query Tool

| | Cost |
|---|---|
| SQLite (local file) | **$0 always** |
| Production: RDS/Azure SQL | ~$15/month |

The sample database is auto-created as a SQLite file. No cloud database needed for development.

### Conversation Store

| Option | Cost/month | Persistence | Scales to zero? |
|---|---|---|---|
| **In-memory** | $0 | Restart = lost | N/A |
| **SQLite** | $0 | Local file | N/A |
| **AWS DynamoDB** | ~$0–5 | Yes | Yes (free tier) |
| **Azure Cosmos DB** | ~$0–5 | Yes | Yes (free tier) |

**What we chose:**
- **Development:** In-memory or SQLite (no cloud needed)
- **Production:** DynamoDB/Cosmos DB (managed, scalable, generous free tiers)

---

## What Alternatives Cost More

### Alternative 1: OpenAI Assistants API instead of LangGraph

| | LangGraph (our choice) | OpenAI Assistants |
|---|---|---|
| **Provider** | Any (Bedrock, Azure, Ollama) | OpenAI only |
| **Tool execution** | Local (you control it) | OpenAI runs it (black box) |
| **Cost** | Pay-per-token (any provider) | $0.20/session + per-token |
| **Persistence** | Self-managed | OpenAI manages |
| **Learning value** | High (build the agent loop) | Low (API call) |

**Why LangGraph is better:** Multi-provider support, full control over tool execution, no per-session fees, and building the agent graph teaches state machine patterns.

### Alternative 2: AWS Bedrock Agents instead of custom

| | Custom LangGraph agent (our choice) | Bedrock Agents |
|---|---|---|
| **Provider** | Any | AWS only |
| **Customisation** | Full control | Limited to Bedrock patterns |
| **Cost** | Per-token only | Per-token + agent session fees |
| **Tools** | Any (custom) | Lambda functions only |
| **Local development** | Yes (Ollama) | No |

**Why custom is better for a portfolio:** Bedrock Agents are AWS-locked. Our agent works with any provider and demonstrates engineering skills.

### Alternative 3: CrewAI for single-agent instead of LangGraph

| | LangGraph (our choice) | CrewAI |
|---|---|---|
| **Best for** | Single agent with tools | Multi-agent collaboration |
| **Complexity** | Medium (state graph) | Lower (declarative) |
| **Control** | Fine-grained (node by node) | Higher-level abstraction |

**Why LangGraph is better for V3:** Single-agent tool use is LangGraph's sweet spot. CrewAI is used in V5 where we need multi-agent collaboration.

---

## Decision Summary

| Decision | Chosen | Alternative | Why chosen wins |
|---|---|---|---|
| Agent framework | LangGraph | OpenAI Assistants / Bedrock Agents | Multi-provider, full control, learning value |
| Web search | Tavily (+ mock fallback) | SerpAPI / Google Custom Search | Free tier, simple API, good results |
| Calculator | AST-based Python | Wolfram Alpha API | $0, no API key, fast, safe |
| Database | SQLite (local) | PostgreSQL | Zero setup, embedded, good enough |
| Conversation store | SQLite / In-memory | DynamoDB / Cosmos DB | $0 for development |

---

## How to Minimise Costs on Personal Account

1. **Use Ollama for development** — All LLM calls are $0 (agent queries would cost $0.025 each on cloud)
2. **Use mock web search** — Don't set `TAVILY_API_KEY` and the agent uses mock results
3. **Use SQLite for conversations** — No cloud database needed
4. **Limit `max_iterations`** — Default 15 is safe; lower to 5 for cost-conscious testing
5. **Set billing alerts** — $10/month budget threshold

---

## Cost of Running Tests on Cloud

| Provider | LLM Calls | Avg Tokens/Call | Token Cost | Total per Run |
|---|---|---|---|---|
| **Local (Ollama)** | ~50 | ~1500 | $0 | **$0** |
| **AWS (Bedrock)** | ~50 | ~1500 | ~$1.50 | **~$1.50** |
| **Azure (OpenAI)** | ~50 | ~1500 | ~$1.15 | **~$1.15** |

> Agent tests cost more than simple chat tests because each test triggers multiple LLM calls (the Think → Act → Observe loop). **Run locally first**, then once on cloud to verify.

---

## Budget Guard — Automatic Cost Protection

Both `infra/aws/` and `infra/azure/` include a **budget guard** (`budget.tf`) that automatically protects against runaway cloud costs.

### How it works

| Threshold | Action |
|---|---|
| **80% of limit (€4)** | Email warning sent to `alert_email` |
| **100% of limit (€5)** | Email + automatic resource kill switch triggered |

### AWS

- **AWS Budget** monitors tagged resources (`project=ai-agent`)
- **SNS → Lambda** pipeline: at 100%, a Lambda function scales ECS to 0 and deletes DynamoDB tables
- File: `infra/aws/budget.tf` + `infra/aws/budget_killer_lambda/handler.py`

### Azure

- **Azure Consumption Budget** scoped to the resource group
- **Action Group → Automation Runbook**: at 100%, a PowerShell runbook deletes all resources in the resource group
- File: `infra/azure/budget.tf`

### Configuration

```hcl
variable "cost_limit_eur" {
  default = 5  # €5 kill switch
}

variable "alert_email" {
  # Required — where budget warnings go
}
```

### ⚠️ Important caveat

Cloud cost reporting has a **6–24 hour lag**. The budget guard is your **safety net**, not your primary defense. Always run:

```bash
terraform destroy  # immediately after finishing labs
```
