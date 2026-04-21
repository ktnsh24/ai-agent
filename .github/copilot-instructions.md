# AI Agent — Copilot Instructions

This is an AI agent that uses LLM function-calling to select and invoke tools (calculator, database, web search) with multi-turn conversation support.

## Architecture
- FastAPI server with tool registry
- LLM-based tool selection via function calling
- Session-based conversation history
- Streaming support via SSE

## Lab Runner
- `scripts/run_all_labs.py` — automated lab runner with crash resilience
- `scripts/start-resilient-server.sh` — auto-restart wrapper for the server
- Lab results go in `scripts/lab_results/`

## Key Patterns
- Tool registry with schema-based discovery
- `api()` helper function for all HTTP calls (with retry logic)
- Health endpoint at `/health` for dependency checks
