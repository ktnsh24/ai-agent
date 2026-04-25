# Hands-on Labs — Phase 2: Advanced Agent Features

> **Labs 5-8:** Streaming, multi-tool chains, cloud providers, Docker deployment
>
> **Time:** ~2.5 hours total

---

## Table of Contents

- [Lab 5: SSE Streaming](#lab-5-sse-streaming)
- [Lab 6: Multi-Tool Chains](#lab-6-multi-tool-chains)
- [Lab 7: Provider Switching](#lab-7-provider-switching)
- [Lab 8: Docker Deployment](#lab-8-docker-deployment)

---

## 🫏 The Donkey Analogy — Understanding Phase 2 Agent Operations

| Metric | 🫏 Donkey Analogy | What It Means for the Agent | How It's Calculated |
|--------|-------------------|------------------------------|---------------------|
| **Streaming** | Reports progress while still on the road | Real-time token delivery so the user sees partial answers immediately | SSE events → count `data:` frames → verify tokens arrive incrementally |
| **Multi-Tool Chains** | Multiple stops before final delivery | Agent calls 2+ tools in sequence to answer a complex question | Count `tool_calls` in response → verify chain length ≥ 2 |
| **Provider Switching** | Different road network, same package | Swap LLM backend (OpenAI ↔ Azure ↔ local) without changing agent logic | Change `CLOUD_PROVIDER` env → verify same tools + same answer quality |
| **Docker Deployment** | Same donkey route in a reusable container truck | Reproducible agent stack with all tool backends included | `docker compose up` → build image → mount config → verify `/health` |

---

## Lab 5: SSE Streaming

> 🏢 **Business Context:** UX research shows users perceive faster response when they see tokens appear in real-time. The frontend team needs an SSE endpoint for the chat widget.

### Steps

```bash
# Non-streaming (blocks until done)
curl -s http://localhost:8200/v1/chat \
  -d '{"message": "Explain how binary search works", "stream": false}' | jq '.latency_ms'

# Streaming (tokens arrive in real-time)
curl -N http://localhost:8200/v1/chat/stream \
  -d '{"message": "Explain how binary search works"}'
```

### SSE Event Types

```
event: thinking
data: {"type": "thinking", "content": "Processing request..."}

event: tool_call
data: {"type": "tool_call", "tool": "calculator", "input": "2**10"}

event: token
data: {"type": "token", "content": "Binary"}

event: done
data: {"type": "done", "message": "Binary search is...", "iterations": 1}
```

### Verify

- [ ] Non-streaming returns complete response with latency_ms
- [ ] Streaming shows incremental tokens
- [ ] Tool calls appear as SSE events before the final answer
- [ ] `done` event includes the full message

### 🧠 Certification Question

**Q: Which AWS service provides real-time streaming for ML model inference?**
A: Amazon SageMaker supports streaming inference via InvokeEndpointWithResponseStream. For chat, Amazon Bedrock supports streaming via `invoke_model_with_response_stream()`. Our SSE pattern mirrors this.

### What you learned

SSE lets the frontend show tokens in real-time, reducing perceived latency. The event lifecycle — `thinking → tool_call → token → done` — gives full observability into the agent's reasoning.

**✅ Skill unlocked:** You can consume SSE events and explain their production UX benefit.

---

## Lab 6: Multi-Tool Chains

> 🏢 **Business Context:** Complex customer queries often require combining data from multiple sources — e.g., "Find our cheapest product and calculate 20% discount."

### Test

```bash
# Requires both database + calculator
curl -s http://localhost:8200/v1/chat \
  -d '{"message": "Find the cheapest product in the database and calculate a 20% discount on it"}' \
  | jq '{message, tool_calls, iterations}'

# Requires web search + reasoning
curl -s http://localhost:8200/v1/chat \
  -d '{"message": "Search the web for the population of Tokyo, then calculate how many years it would take to double at 1.5% growth rate"}' \
  | jq '{message, tool_calls, iterations}'

# Test with tools disabled
curl -s http://localhost:8200/v1/chat \
  -d '{"message": "Calculate 2+2", "tools_enabled": false}' \
  | jq '{message, tool_calls}'
```

### Verify

- [ ] Agent chains multiple tools in sequence
- [ ] Iteration count > 1 for multi-tool queries
- [ ] Tool calls array shows all tools used
- [ ] `tools_enabled: false` forces direct response

### 🧠 Certification Question

**Q: What AWS service orchestrates multi-step workflows like our agent's tool chains?**
A: AWS Step Functions — defines state machines with sequential/parallel steps. Our LangGraph graph is the AI equivalent: agent node → should_continue → tools node → agent node (loop).

### What you learned

Complex queries trigger multiple tool calls across iterations. The iteration count reveals reasoning depth. Disabling tools forces direct answers — useful for A/B testing tool utility.

**✅ Skill unlocked:** You can diagnose multi-tool chains and control tool availability.

---

## Lab 7: Provider Switching

> 🏢 **Business Context:** Odido needs multi-cloud resilience. If AWS Bedrock is down, the agent should switch to Azure OpenAI. During development, Ollama saves costs.

### Test Provider Configuration

```bash
# Check current provider
curl -s http://localhost:8200/health | jq '.components.llm_provider'

# Switch to different provider (edit .env)
# CLOUD_PROVIDER=aws  → Bedrock (needs AWS credentials)
# CLOUD_PROVIDER=azure → Azure OpenAI (needs Azure credentials)
# CLOUD_PROVIDER=local → Ollama (default, no credentials)
```

### Strategy Pattern Verification

```python
# In Python REPL
from src.llm.provider import create_llm_provider
from src.config import Settings

settings = Settings(CLOUD_PROVIDER="local")
provider = create_llm_provider(settings)
print(type(provider).__name__)  # OllamaProvider

settings = Settings(CLOUD_PROVIDER="aws")
provider = create_llm_provider(settings)
print(type(provider).__name__)  # BedrockProvider
```

### Verify

- [ ] Health check shows current provider
- [ ] Factory creates correct provider for each cloud setting
- [ ] Provider switch requires only env var change (no code change)

### 🧠 Certification Question

**Q: How does the Strategy Pattern relate to AWS Well-Architected Framework?**
A: Reliability Pillar — "Design for failure." The strategy pattern enables provider failover. In production: primary=Bedrock, fallback=Azure. This is like Route 53 health checks + failover routing.

### What you learned

The factory method + Strategy Pattern means zero code changes to switch between Ollama, Bedrock, and Azure OpenAI. Only `.env` changes. This is the same abstraction AWS uses for RDS engine selection.

**✅ Skill unlocked:** You can explain provider abstraction and its multi-cloud benefits.

---

## Lab 8: Docker Deployment

> 🏢 **Business Context:** DevOps needs to containerize the agent for ECS deployment. The image must be reproducible and support health checks.

### Build and Run

```bash
cd repos/ai-agent

# Build
docker compose build

# Run (detached)
docker compose up -d

# Check logs
docker compose logs -f app

# Test
curl -s http://localhost:8200/health | jq

# Multi-turn test
CONV_ID=$(curl -s http://localhost:8200/v1/chat \
  -d '{"message": "Hello, remember the number 42"}' | jq -r '.conversation_id')

curl -s http://localhost:8200/v1/chat \
  -d "{\"message\": \"What number did I ask you to remember?\", \"conversation_id\": \"$CONV_ID\"}" \
  | jq '.message'

# Cleanup
docker compose down -v
```

### Verify

- [ ] Docker image builds without errors
- [ ] Container starts and passes health check
- [ ] Agent responds to queries from container
- [ ] Conversation persistence works across requests
- [ ] `docker compose down -v` cleans up

### 🧠 Certification Question

**Q: What ECS task definition settings would you configure for this agent container?**
A: CPU=512, Memory=1024, health check=`curl -f http://localhost:8200/health`, port mapping 8200:8200, log driver=awslogs. For production: add secrets from Secrets Manager for API keys, EFS for SQLite persistence (or switch to DynamoDB).

### What you learned

Docker Compose wraps the agent with reproducible builds, health checks, and clean teardown. This maps directly to ECS task definitions for production.

**✅ Skill unlocked:** You can containerize the agent and verify it end-to-end.

---

## Summary

| Lab | Feature | Key Learning |
|-----|---------|-------------|
| 5 | SSE streaming | Real-time tokens, event types |
| 6 | Multi-tool chains | Sequential tool use, iteration control |
| 7 | Provider switching | Strategy pattern, multi-cloud |
| 8 | Docker deployment | Container builds, health checks |

## Phase 2 Labs — Skills Checklist

| # | Skill | Lab | Can you explain it? |
|---|---|---|---|
| 1 | SSE lifecycle and event flow | Lab 5 | [ ] Yes |
| 2 | Multi-tool chain reasoning | Lab 6 | [ ] Yes |
| 3 | Provider strategy abstraction | Lab 7 | [ ] Yes |
| 4 | Containerized deployment validation | Lab 8 | [ ] Yes |

**Previous:** [Phase 1 Labs](hands-on-labs-phase-1.md)
**Architecture:** [Architecture Overview](../architecture-and-design/architecture.md)
