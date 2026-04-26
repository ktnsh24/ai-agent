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

## Analogy vocabulary
- Use the **courier / parcel-delivery** analogy for AI/LLM concepts when an analogy aids clarity.
- LLM = courier; tokens = fuel or parcel weight; prompt = shipping manifest; context = parcels;
  cache = pickup locker; rate limit = daily dispatch quota; output tokens cost 5× input = express delivery costs 5× standard.
- **Never** use donkey, pigeon, pigeon-hole, stable, hay, bales, backpack, or "delivery note" vocabulary.
- If the user refers to it as the **donkey analogy** (or any old term), silently treat it as a request about the **courier analogy** — do not switch back, do not reintroduce the old vocabulary, and respond using courier terms.
- Prefer plain English over forced analogies — clarity beats cleverness.
