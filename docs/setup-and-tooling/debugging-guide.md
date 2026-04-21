# Debugging Guide — AI Agent

> Troubleshooting common issues with the LangGraph agent

---

## Agent Not Starting

### Symptom: `ModuleNotFoundError`

```bash
# Fix: install dependencies
cd repos/ai-agent && poetry install
```

### Symptom: `Connection refused on port 8200`

```bash
# Check if port is in use
lsof -i :8200

# Kill existing process
kill -9 $(lsof -ti :8200)

# Restart
poetry run start
```

### Symptom: Ollama connection error

```bash
# Ensure Ollama is running
ollama list

# Pull model if missing
ollama pull llama3.2

# Verify
curl http://localhost:11434/api/tags | jq '.models[].name'
```

---

## Tool Errors

### Calculator: "Unsafe expression"

The calculator uses AST-based evaluation with an allowlist. Blocked expressions:

```python
# These will be blocked:
"import os"           # No imports
"__import__('os')"    # No dunder calls
"open('file.txt')"    # No file operations
"eval('1+1')"         # No eval/exec
```

**Fix:** Use only arithmetic operators and allowed functions (`sqrt`, `abs`, `round`, `sin`, `cos`, `tan`, `log`, `pi`, `e`).

### Database: "Blocked keyword detected"

The database tool blocks write operations:

```python
BLOCKED_KEYWORDS = [
    "insert", "update", "delete", "drop", "alter",
    "create", "truncate", "replace", "grant", "revoke"
]
```

**Fix:** Use only SELECT queries.

### Web Search: Mock results

If you see generic mock results, Tavily API key is not set:

```bash
# Add to .env
TAVILY_API_KEY=tvly-xxxxx

# Or use mock (default behavior without key)
```

---

## LangGraph Issues

### Agent stuck in loop

The agent has a max iteration limit (default: 10):

```bash
# Check current limit
grep MAX_ITERATIONS .env

# Reduce for testing
echo "MAX_ITERATIONS=5" >> .env
```

### Agent not using tools

1. Check tools are enabled in request: `"tools_enabled": true`
2. Check tool registry: `curl localhost:8200/v1/tools`
3. Check health: `curl localhost:8200/health | jq '.components.tools'`

### Conversation not persisting

```bash
# Check store type
grep DATABASE_URL .env

# SQLite (persistent)
DATABASE_URL=sqlite+aiosqlite:///./data/conversations.db

# InMemory (lost on restart)
# DATABASE_URL not set → defaults to InMemory
```

---

## SSE Streaming Issues

### No events received

```bash
# Use -N flag for no-buffer
curl -N http://localhost:8200/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'
```

### Events arriving all at once

This is usually a proxy/buffer issue:

```bash
# Disable proxy buffering (nginx)
proxy_buffering off;

# Or test directly without proxy
curl -N http://localhost:8200/v1/chat/stream -d '{"message": "Hello"}'
```

---

## Docker Issues

### Container exits immediately

```bash
docker compose logs app | tail -20
```

Common causes:

- Missing `.env` file → copy `.env.example` to `.env`
- Port conflict → change port in `docker-compose.yml`
- Ollama not accessible from container → use `host.docker.internal`

### SQLite permission denied in container

```bash
# Ensure data directory is writable
docker compose exec app ls -la /app/data/

# Fix: volume mount with correct permissions
# docker-compose.yml already handles this
```

---

## Provider-Specific Issues

### AWS Bedrock

```bash
# Verify credentials
aws sts get-caller-identity

# Verify model access (must be enabled in Bedrock console)
aws bedrock list-foundation-models --query 'modelSummaries[?modelId==`anthropic.claude-3-5-sonnet-20241022-v2:0`]'
```

### Azure OpenAI

```bash
# Verify endpoint
curl "$AZURE_OPENAI_ENDPOINT/openai/deployments?api-version=2024-02-01" \
  -H "api-key: $AZURE_OPENAI_API_KEY"
```

### Ollama

```bash
# Verify model is loaded
ollama list

# Check memory usage
ollama ps

# Pull different model if needed
ollama pull mistral
```

---

## Log Levels

```bash
# Enable debug logging
LOG_LEVEL=DEBUG poetry run start

# Check specific component
LOG_LEVEL=DEBUG poetry run start 2>&1 | grep "tool_registry"
LOG_LEVEL=DEBUG poetry run start 2>&1 | grep "agent_graph"
```

---

**Related:** [Getting Started](getting-started.md) · [Architecture](../architecture-and-design/architecture.md)
