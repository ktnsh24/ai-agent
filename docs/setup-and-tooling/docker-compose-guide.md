# Docker Compose Guide — AI Agent

> **Service:** `app` (FastAPI + LangGraph agent)
>
> **File:** `docker-compose.yml`

The Docker Compose setup runs the agent in `local` mode — it connects to an Ollama instance running on the host machine instead of a cloud LLM provider. No cloud credentials are needed.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Quick Start](#2-quick-start)
3. [Service Details](#3-service-details)
4. [Switching LLM Providers](#4-switching-llm-providers)
5. [Common Commands](#5-common-commands)
6. [Troubleshooting](#6-troubleshooting)
7. [Cross-References](#7-cross-references)

---

## 1. Prerequisites

| Requirement | Notes |
|-------------|-------|
| Docker + Docker Compose | Any recent version |
| Ollama running on host port 11434 | **Local mode only** — pull a model first: `ollama pull llama3.2` |

Ollama must be running before `docker compose up`. The agent will start but every chat request will fail with a connection error if Ollama is not available.

---

## 2. Quick Start

```bash
# Start the agent
docker compose up -d

# Check it is running
docker compose ps

# Verify the agent is healthy
curl http://localhost:8200/health

# Watch logs
docker compose logs -f app

# Stop
docker compose down
```

The agent is available at `http://localhost:8200` once the container is up.

---

## 3. Service Details

### `app` — AI Agent

```yaml
app:
  build: .
  ports:
    - "8200:8200"
  environment:
    - CLOUD_PROVIDER=local
    - OLLAMA_BASE_URL=http://host.docker.internal:11434
    - DATABASE_URL=sqlite+aiosqlite:///data/conversations.db
    - TOOL_WEB_SEARCH_ENABLED=true
    - TOOL_CALCULATOR_ENABLED=true
    - TOOL_DATABASE_QUERY_ENABLED=true
  volumes:
    - agent_data:/app/data
  extra_hosts:
    - "host.docker.internal:host-gateway"
  restart: unless-stopped
```

**Key points:**

- `CLOUD_PROVIDER=local` — tells the agent to use Ollama instead of a cloud LLM. Change this to `aws` or `azure` for cloud deployment (see section 4).
- `extra_hosts: host.docker.internal:host-gateway` — required on Linux to resolve `host.docker.internal` and reach Ollama on the host. This line is a no-op on macOS/Windows where Docker Desktop handles it automatically.
- `agent_data:/app/data` — named volume that persists the SQLite conversation database across container restarts. Removing the volume clears all conversation history.
- `restart: unless-stopped` — the container restarts automatically after a crash or host reboot, but not if you stopped it manually with `docker compose down`.

### Volumes

```yaml
volumes:
  agent_data:
```

A single named volume mounts at `/app/data` inside the container. The SQLite database file (`conversations.db`) lives here. To inspect it:

```bash
docker compose exec app sqlite3 /app/data/conversations.db ".tables"
```

To wipe all conversations and start fresh:

```bash
docker compose down -v
docker compose up -d
```

---

## 4. Switching LLM Providers

The agent supports three provider modes. Change the environment variables to switch:

### Local (Ollama — default)

```yaml
environment:
  - CLOUD_PROVIDER=local
  - OLLAMA_BASE_URL=http://host.docker.internal:11434
```

Requires Ollama running on port 11434 with a model pulled (e.g. `ollama pull llama3.2`).

### AWS (Bedrock)

```yaml
environment:
  - CLOUD_PROVIDER=aws
  - AWS_REGION=eu-west-1
  - AWS_ACCESS_KEY_ID=...
  - AWS_SECRET_ACCESS_KEY=...
```

Or mount AWS credentials from `~/.aws` rather than hardcoding them.

### Azure (OpenAI)

```yaml
environment:
  - CLOUD_PROVIDER=azure
  - AZURE_OPENAI_ENDPOINT=https://...
  - AZURE_OPENAI_API_KEY=...
  - AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
```

---

## 5. Common Commands

### Start / Stop

```bash
# Start in background
docker compose up -d

# Start and watch logs (foreground)
docker compose up

# Stop containers (keeps volumes)
docker compose down

# Stop and delete volumes (wipes conversation history)
docker compose down -v
```

### Logs

```bash
# Tail all logs
docker compose logs -f

# Tail app only
docker compose logs -f app

# Last 100 lines
docker compose logs --tail=100 app
```

### Rebuild

```bash
# Rebuild after code changes
docker compose up -d --build app

# Force full rebuild (no layer cache)
docker compose build --no-cache app
docker compose up -d
```

### Debugging

```bash
# Shell into the container
docker compose exec app bash

# Check the SQLite DB directly
docker compose exec app sqlite3 /app/data/conversations.db ".tables"
docker compose exec app sqlite3 /app/data/conversations.db "SELECT * FROM conversations LIMIT 5;"

# Send a test chat request
curl -X POST http://localhost:8200/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello! What tools do you have?"}'
```

---

## 6. Troubleshooting

### Ollama not accessible from container

```
Error: Cannot connect to Ollama at host.docker.internal:11434
```

Fix:
```bash
# Verify Ollama is running on the host
curl http://localhost:11434/api/tags

# Verify host.docker.internal resolves inside the container
docker compose exec app curl http://host.docker.internal:11434/api/tags

# If on Linux and still failing, check the extra_hosts line is present
# in docker-compose.yml:
#   extra_hosts:
#     - "host.docker.internal:host-gateway"
```

### Port 8200 already in use

```
Error: Bind for 0.0.0.0:8200 failed: port is already allocated
```

Fix:
```bash
# Find what is using the port
lsof -i :8200

# Kill it, or change the host port in docker-compose.yml:
#   ports:
#     - "8201:8200"
```

### Health check returns `degraded`

```bash
# Check which component is failing
curl http://localhost:8200/health | python3 -m json.tool

# Check logs for the failing component
docker compose logs --tail=50 app
```

Common causes: Ollama is not running (`llm_provider` degraded), or the data volume has a corrupted SQLite file (`conversation_store` degraded).

### Conversation history lost after restart

This means the `agent_data` volume was deleted (e.g., `docker compose down -v`). Volumes are the only persistence layer — no external database is used in local mode. To avoid this, always use `docker compose down` (without `-v`) to stop the service.

---

## 7. Cross-References

| Topic | Document | 🚚 Courier |
|-------|----------|-----------|
| Getting started | [Getting Started](getting-started.md) | The orientation pack that walks a new engineer through setting up the full dispatch desk from scratch. |
| Architecture | [Architecture Overview](../architecture-and-design/architecture.md) | The full depot blueprint explaining how the dispatch desk, LangGraph loop, and conversation store all connect. |
| Terraform (cloud) | [Terraform Guide](terraform-guide.md) | The blueprint guide for stamping out a full cloud depot on AWS or Azure with a single `terraform apply`. |
| Debugging | [Debugging Guide](debugging-guide.md) | The troubleshooting manual for diagnosing failed agent loops, tool errors, and provider connectivity issues. |
