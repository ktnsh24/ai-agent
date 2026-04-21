# Hands-on Labs — Phase 1: Agent Foundation

> **Labs 1-4:** Build and test the core AI agent capabilities
> **Time:** ~2 hours total

---

## Table of Contents

- [Cost Estimation — Local vs Cloud](#cost-estimation--local-vs-cloud)
- [Lab 1: First Agent Interaction](#lab-1-first-agent-interaction)
- [Lab 2: Tool Exploration](#lab-2-tool-exploration)
- [Lab 3: Conversation Continuity](#lab-3-conversation-continuity)
- [Lab 4: Health Check and Monitoring](#lab-4-health-check-and-monitoring)

---

## Cost Estimation — Local vs Cloud

All labs run **locally for free**. Cloud costs if you deploy:

| Stack | Per lab session (~30 queries) | Monthly (always on) | Best for |
|-------|-------------------------------|---------------------|----------|
| **Local (Ollama)** | $0 | $0 | Learning, experimenting |
| **AWS (cheapest)** | ~$0.02 | ~$8/mo (Fargate 0.25 vCPU) | Proving cloud skills |
| **Azure (cheapest)** | ~$0.01 | ~$0 (Container Apps free tier) | Best free tier |

<details>
<summary>Detailed AWS breakdown</summary>

| Component | AWS Service | Cost |
|-----------|-------------|------|
| LLM | Bedrock (Claude 3 Haiku) | ~$0.02/session |
| Conversation store | DynamoDB (free tier) | $0 |
| API server | ECS Fargate (0.25 vCPU) | ~$8/mo |
| Logs | CloudWatch | $0 (free tier) |

</details>

<details>
<summary>Detailed Azure breakdown</summary>

| Component | Azure Service | Cost |
|-----------|---------------|------|
| LLM | Azure OpenAI (GPT-4o mini) | ~$0.01/session |
| Conversation store | Cosmos DB (free tier: 1000 RU/s) | $0 |
| API server | Container Apps (free tier) | $0 |
| Logs | Azure Monitor | $0 |

</details>

---

## 🫏 The Donkey Analogy — Understanding Phase 1 Agent Metrics

| Metric | 🫏 Donkey Analogy | What It Means for the Agent | How It's Calculated |
|--------|-------------------|------------------------------|---------------------|
| **Tool Selection** | Picks the right route — direct path vs. specialist stations | Agent decides whether to call tools or answer directly | LLM function-calling → match intent to tool schema → invoke or skip |
| **Tool Accuracy** | Visits the *correct* specialist station, not a random one | The right tool is chosen for the task (calculator for math, DB for data) | Compare `tool_name` in response vs. expected tool for the query type |
| **Conversation Continuity** | Carries context between villages instead of starting over | Multi-turn memory so follow-up questions work without repeating context | Session ID → append to conversation history → include in next LLM prompt |
| **Service Health** | Checks the donkey is alive and ready for jobs | Confirms agent, LLM provider, and tool backends are all reachable | `GET /health` → poll each dependency → return aggregate status |
| **Latency** | How quickly the donkey completes the delivery | End-to-end time from question to final answer, including any tool calls | `time_end − time_start` across full agent loop (ms) |
| **Direct vs. Tool Response** | Shortest path (no stops) vs. multi-stop route | Whether the agent correctly identifies when tools are needed vs. not | Check response metadata: `tool_calls` field present or absent |

---

## Lab 1: First Agent Interaction

> 🏢 **Business Context:** The product team wants a smart assistant that can answer questions, perform calculations, and look up data — not just generate text. The agent must decide when to use tools vs respond directly.

### Steps

```bash
cd repos/ai-agent && poetry install
cp .env.example .env
ollama pull llama3.2
poetry run start
```

### Test

```bash
# Simple question (no tools)
curl -s http://localhost:8200/v1/chat \
  -d '{"message": "What is the capital of Japan?"}' | jq '{message, iterations, tool_calls}'

# Tool-using question
curl -s http://localhost:8200/v1/chat \
  -d '{"message": "Calculate 2^10 + sqrt(144)"}' | jq '{message, iterations, tool_calls}'
```

### Verify

- [ ] Simple questions get direct answers (0 tool calls)
- [ ] Math questions trigger calculator tool
- [ ] Response includes iterations count and tool call details

### 🧠 Certification Question

**Q: What AWS service enables serverless function execution similar to our agent's tool calls?**
A: AWS Lambda — tools are like Lambda functions invoked by the agent. Step Functions orchestrates them, similar to LangGraph's state machine.

### What you learned

The agent's ReAct loop decides whether to answer directly or delegate to a tool. Simple factual questions get 0 tool calls; questions requiring computation trigger the calculator. This tool-selection decision is the core of agent intelligence — and the first thing to debug when answers are wrong.

**✅ Skill unlocked:** You can distinguish tool-assisted from direct responses and interpret iteration counts.

---

## Lab 2: Tool Exploration

> 🏢 **Business Context:** Different teams need different capabilities: finance needs calculations, marketing needs web search, analytics needs database queries.

### Test Each Tool

```bash
# Calculator
curl -s http://localhost:8200/v1/chat \
  -d '{"message": "What is (15 * 24) + sqrt(625)?"}' | jq '.tool_calls'

# Database query
curl -s http://localhost:8200/v1/chat \
  -d '{"message": "What are the top 3 most expensive products in the database?"}' | jq '.tool_calls'

# Web search (mock without Tavily key)
curl -s http://localhost:8200/v1/chat \
  -d '{"message": "Search the web for latest AI news"}' | jq '.tool_calls'

# List all tools
curl -s http://localhost:8200/v1/tools | jq
```

### Verify

- [ ] Calculator returns correct numeric answers
- [ ] Database queries return formatted table data
- [ ] Web search returns results (mock or real)
- [ ] Tools endpoint lists all available tools

### 🧠 Certification Question

**Q: How does an AI agent select which tool to invoke for a given query?**
A: The LLM analyzes the user's intent and matches it against each tool's description and input schema. This is function calling — the same mechanism behind AWS Bedrock's tool-use API and OpenAI's function calling.

### What you learned

Each tool has a specific purpose and input schema. The agent selects the right tool based on the question's intent. The `/v1/tools` endpoint provides discovery — essential for any MCP-style integration.

**✅ Skill unlocked:** You can enumerate tools, test each one independently, and verify correct tool selection.

---

## Lab 3: Conversation Continuity

> 🏢 **Business Context:** Customer support agents need memory — a customer shouldn't have to repeat their issue every message.

### Test Multi-Turn Conversation

```bash
# Start conversation
RESPONSE=$(curl -s http://localhost:8200/v1/chat \
  -d '{"message": "My name is Ketan and I work at Odido."}')
echo $RESPONSE | jq '{message, conversation_id}'
CONV_ID=$(echo $RESPONSE | jq -r '.conversation_id')

# Continue (agent should remember)
curl -s http://localhost:8200/v1/chat \
  -d "{\"message\": \"What is my name and where do I work?\", \"conversation_id\": \"$CONV_ID\"}" | jq '.message'

# List conversations
curl -s http://localhost:8200/v1/conversations | jq

# Get conversation detail
curl -s http://localhost:8200/v1/conversations/$CONV_ID | jq '.messages | length'

# Delete conversation
curl -s -X DELETE http://localhost:8200/v1/conversations/$CONV_ID | jq
```

### Verify

- [ ] Agent remembers context from earlier messages
- [ ] Conversation list shows the conversation
- [ ] Conversation detail includes all messages
- [ ] Delete removes the conversation

### 🧠 Certification Question

**Q: Why do production AI agents need a persistence layer for conversations?**
A: Without persistence, every request is stateless — the agent forgets previous messages. DynamoDB (or similar) stores conversation history keyed by session ID, enabling multi-turn context. This maps to the AWS Well-Architected reliability pillar.

### What you learned

Conversation IDs enable multi-turn memory. Without them, every request is stateless. The CRUD lifecycle (create → read → list → delete) mirrors how DynamoDB or any persistence layer manages session state in production.

**✅ Skill unlocked:** You can manage conversation lifecycle and explain why stateful agents need persistence.

---

## Lab 4: Health Check and Monitoring

> 🏢 **Business Context:** SRE team needs visibility into agent health, available tools, and conversation count.

### Test

```bash
curl -s http://localhost:8200/health | jq
```

### Expected

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "provider": "local",
  "components": {
    "llm_provider": "ready (local)",
    "model": "llama3.2",
    "tools": "3 tools available",
    "tool_names": "web_search, calculator, database_query",
    "conversation_store": "ready (0 conversations)",
    "agent_graph": "compiled"
  }
}
```

### Verify

- [ ] Health check returns all component statuses
- [ ] Provider and model are correct
- [ ] Tool count matches configuration

### 🧠 Certification Question

**Q: What AWS service performs health checks on application targets, and what happens when a check fails?**
A: ALB target group health checks poll endpoints like `/health`. If a target fails consecutive checks, ALB stops routing traffic to it — this is exactly what our health endpoint enables in ECS deployments.

### What you learned

Health checks expose component readiness — LLM provider, tools, conversation store, and the compiled agent graph. This is what ALB target groups poll in production. A degraded component (e.g., Ollama down) should change the status, not crash the server.

**✅ Skill unlocked:** You can interpret agent health output and map components to production monitoring.

---

## Summary

| Lab | Component | Key Learning |
|-----|-----------|-------------|
| 1 | Agent core | ReAct loop, tool vs direct response |
| 2 | Tools | Calculator, DB query, web search |
| 3 | Conversations | Multi-turn memory, CRUD |
| 4 | Health check | Component monitoring |

## Phase 1 Labs — Skills Checklist

| # | Skill | Lab | Can you explain it? |
|---|---|---|---|
| 1 | Direct vs tool-assisted responses | Lab 1 | [ ] Yes |
| 2 | Tool selection and capabilities | Lab 2 | [ ] Yes |
| 3 | Conversation continuity and lifecycle | Lab 3 | [ ] Yes |
| 4 | Agent health component interpretation | Lab 4 | [ ] Yes |

**Next:** [Phase 2 Labs](hands-on-labs-phase-2.md) — SSE streaming, multi-tool chains, Docker deployment.
