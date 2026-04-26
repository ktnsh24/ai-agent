# Monitoring

> The agent's logbook — what we record, where it goes, and how to read it. The agent emits structured logs and a health endpoint; this page is the honest index of what observability actually exists today.

> **Related docs:**
>
> - [Health Endpoint](../architecture-and-design/api-routes/health-endpoint-explained.md) — the four-component liveness probe
> - [Infrastructure Explained](../architecture-and-design/infra-explained.md) — CloudWatch log destinations
> - [LangGraph Deep Dive](../ai-engineering/langgraph-deep-dive.md) — agent loop internals that generate the log events

---

## Table of Contents

- [What We Monitor](#what-we-monitor)
- [What We Do Not Have](#what-we-do-not-have)
- [Health Check](#health-check)
- [Log Aggregation](#log-aggregation)
- [Tool Call Visibility](#tool-call-visibility)
- [Courier Explainer](#courier-explainer)

---

## What We Monitor

The agent has two observability surfaces:

| Surface | Source | Storage | Query path | 🚚 Courier |
|---------|--------|---------|------------|-----------|
| Structured logs | Python `logging` module; JSON-formatted in production via uvicorn | stdout/stderr → CloudWatch `/ecs/{name_prefix}` (AWS) or Container Apps log stream (Azure) | `aws logs tail` / `az containerapp logs show` | Tachograph tape from every courier delivery — method, path, status, and any tool calls made. |
| Health probe | `GET /health` checks all four agent components | Response payload only (no persistence) | Load balancer / ECS health checks, or manual `curl /health` | Front-porch lamp — watchman glances at it to see whether the courier, registry, store, and graph are all lit. |

This is **basic logging only**. No observability stack (Prometheus, Grafana, LangFuse, Datadog) is wired in. The signals listed above are what exist today.

- 🚚 **Courier:** Two signal feeds on the monitoring wall — tachograph tape in the log shed, and a health indicator at the front door. Together they tell the operator whether the agent is alive and what it has been doing.

---

## What We Do Not Have

This section exists to prevent false assumptions when coming from rag-chatbot or ai-gateway.

| Capability | Status | Note |
|------------|--------|------|
| LangFuse integration | ❌ Not present | rag-chatbot has this; ai-agent does not |
| Prometheus `/metrics` endpoint | ❌ Not present | rag-chatbot has this; ai-agent does not |
| Request ID middleware (`X-Request-ID`) | ❌ Not present | ai-gateway has this; ai-agent does not |
| Cost tracking / cost log table | ❌ Not present | ai-gateway has this; ai-agent does not |
| Real token counting | ❌ Not present | Token count is **estimated** as `chars // 4` — not actual tokeniser output |
| Grafana / CloudWatch dashboard | ❌ Not shipped | No dashboard JSON in the repo |
| Alerting rules | ❌ Not shipped | No alert configuration exists; budget alarm only |

---

## Health Check

`GET /health` is the primary readiness signal. It checks four components synchronously and returns an overall status:

| Component | What is checked | Healthy value | 🚚 Courier |
|-----------|----------------|---------------|-----------|
| `llm_provider` | LLM provider configuration is reachable / initialised | String does not contain `"error"` | Is the courier on shift and holding a valid route card? |
| `tool_registry` | Tool registry loaded with at least one tool | String does not contain `"error"` | Is the specialist directory populated and accessible? |
| `conversation_store` | SQLite / async DB connection is live | String does not contain `"error"` | Is the conversation logbook open and writable? |
| `agent_graph` | LangGraph StateGraph compiled without error | String does not contain `"error"` | Is the dispatch graph assembled and ready to route a parcel? |

The overall `status` field is `"healthy"` when all four component strings are clean, or `"degraded"` if any component string contains `"error"`. There is no `"unhealthy"` status — degraded is the worst reported state.

```
GET /health

200 OK
{
  "status": "healthy",
  "components": {
    "llm_provider": "openai (gpt-4o-mini)",
    "tool_registry": "3 tools registered",
    "conversation_store": "sqlite connected",
    "agent_graph": "compiled"
  }
}
```

---

## Log Aggregation

| Layer | AWS path | Azure path | 🚚 Courier |
|-------|---------|------------|-----------|
| Container stdout/stderr | CloudWatch Log Group `/ecs/{name_prefix}`, 30-day retention | Container Apps log stream | Tachograph tape rolls into the depot's log shed; stays there for thirty days then is shredded. |
| Log format | JSON via uvicorn in production; plain text in local mode | Same | One structured line per event — parseable by log query tools. |
| Log level | `INFO` by default; set `LOG_LEVEL=DEBUG` to see LangGraph step details | Same | Turn the detail dial up to DEBUG to watch the courier's every step on the delivery route. |

CloudWatch is the **first** place to look for any unexplained behaviour in AWS deployments. Every agent component (router, LangGraph loop, tool calls, conversation store) routes through the Python `logging` module and ends up in the same log group.

To tail logs on AWS:

```bash
aws logs tail /ecs/ai-agent-dev --follow
```

To view logs on Azure:

```bash
az containerapp logs show --name ai-agent-dev --resource-group rg-ai-agent-dev --follow
```

---

## Tool Call Visibility

Every `POST /v1/chat` and `POST /v1/chat/stream` response includes a `tool_calls_made` field in the response body — an ordered list of every tool the agent invoked during that request's LangGraph loop:

```json
{
  "response": "...",
  "tool_calls_made": ["web_search", "calculator"],
  "conversation_id": "abc123",
  "token_count": 214
}
```

This is the primary signal for understanding what the agent did on a given request, without needing to parse logs. `token_count` is an estimate (`chars // 4`), not an exact tokeniser count.

---

## 🚚 Courier Explainer

Monitoring is the agent's logbook — two feeds keep the operator informed:

1. **Structured log lines** — every request, tool call, and LangGraph step emits a log line to stdout. In production (AWS or Azure) those lines land in the cloud log stream (CloudWatch or Container Apps) with 30-day retention.
2. **Health check** — `GET /health` returns a live status for each of the four internal components. Cloud probes call this every few seconds; a degraded response is the first signal that something is wrong.

The monitoring setup is deliberately minimal. There is no cost-tracking database, no request-ID tracing, no LangFuse dashboard, and no Prometheus scrape. The `tool_calls_made` field in every chat response and the log lines in CloudWatch are what exist. For deeper observability, add LangFuse (wiring point: the LangGraph node callbacks) or export structured logs to a SIEM.
