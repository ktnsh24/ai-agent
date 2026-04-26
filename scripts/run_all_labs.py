#!/usr/bin/env python3
"""
Run all hands-on labs for the AI Agent project.

Usage:
    python scripts/run_all_labs.py                    # Run all labs against local
    python scripts/run_all_labs.py --env aws           # Run against AWS
    python scripts/run_all_labs.py --only 1 3          # Run only labs 1 and 3
    python scripts/run_all_labs.py --dry-run            # Print commands without executing

Output:
    scripts/lab_results/local/lab-1-first-interaction.json
    scripts/lab_results/local/lab-2-tool-exploration.json
    ...
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_URLS: dict[str, str] = {
    "local": "http://localhost:8200",
    "aws": "https://ai-agent.dev.example.com",
    "azure": "https://ai-agent.dev.example.com",
}

RESULTS_DIR = Path(__file__).parent / "lab_results"

SERVER_RECOVERY_MAX_WAIT = 120
SERVER_RECOVERY_INTERVAL = 5


@dataclass
class LabResult:
    lab: int
    name: str
    checks: list[dict[str, str | bool]] = field(default_factory=list)
    raw_responses: list[dict] = field(default_factory=list)
    passed: bool = False
    duration_ms: float = 0.0


# ---------------------------------------------------------------------------
# Crash-resilience helpers
# ---------------------------------------------------------------------------

def _wait_for_server(base_url: str, context: str = "") -> bool:
    """Wait for the server to become healthy again after a crash."""
    label = f" (after {context})" if context else ""
    print(f"\n    🔄 Server unreachable{label} — waiting for recovery...", flush=True)
    elapsed = 0
    while elapsed < SERVER_RECOVERY_MAX_WAIT:
        time.sleep(SERVER_RECOVERY_INTERVAL)
        elapsed += SERVER_RECOVERY_INTERVAL
        try:
            resp = httpx.get(f"{base_url}/health", timeout=5)
            if resp.status_code == 200:
                print(f"    ✅ Server recovered after {elapsed}s", flush=True)
                return True
        except Exception:
            pass
        print(f"    ⏳ Still waiting... ({elapsed}s / {SERVER_RECOVERY_MAX_WAIT}s)", flush=True)
    print(f"    ❌ Server did not recover within {SERVER_RECOVERY_MAX_WAIT}s", flush=True)
    return False


def _is_connection_error(e: Exception) -> bool:
    """Check if an exception is a server connection/crash error."""
    msg = str(e).lower()
    return any(pattern in msg for pattern in [
        "connection refused", "server disconnected", "connection reset",
        "connection closed", "remotedisconnected", "broken pipe", "eof occurred",
    ])


def _retry_on_crash(base_url: str, fn, *args, context: str = "", max_retries: int = 2, **kwargs):
    """Call fn(*args, **kwargs) with automatic retry if server crashes."""
    for attempt in range(max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if _is_connection_error(e) and attempt < max_retries:
                if _wait_for_server(base_url, context=f"{context}, attempt {attempt + 1}"):
                    continue
            raise


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def api(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    json_body: dict | None = None,
) -> httpx.Response:
    """Make an API request and return the response."""
    base_url = str(client.base_url).rstrip("/")
    fn = getattr(client, method.lower())
    kwargs: dict = {}
    if json_body is not None:
        kwargs["json"] = json_body
    return _retry_on_crash(base_url, fn, path, context=f"{method} {path}", **kwargs)


def check(result: LabResult, name: str, passed: bool, notes: str = "") -> None:
    result.checks.append({"check": name, "passed": passed, "notes": notes})


def save_result(result: LabResult, env: str) -> None:
    out_dir = RESULTS_DIR / env
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = result.name.lower().replace(" ", "-").replace(":", "")
    path = out_dir / f"lab-{result.lab}-{slug}.json"
    result.passed = all(c["passed"] for c in result.checks)
    data = {
        "lab": result.lab,
        "name": result.name,
        "passed": result.passed,
        "duration_ms": round(result.duration_ms, 1),
        "checks": result.checks,
        "raw_responses": result.raw_responses,
    }
    path.write_text(json.dumps(data, indent=2, default=str))
    status = "PASS" if result.passed else "FAIL"
    print(f"  Lab {result.lab}: {status} ({result.duration_ms:.0f}ms) -> {path.name}")


# ---------------------------------------------------------------------------
# Labs
# ---------------------------------------------------------------------------

def lab_1_first_interaction(client: httpx.Client) -> LabResult:
    """Lab 1: First Agent Interaction — simple question + tool-using question."""
    result = LabResult(lab=1, name="first-interaction")
    t0 = time.time()

    # Simple question (no tools expected)
    r = api(client, "POST", "/v1/chat", json_body={"message": "What is the capital of Japan?"})
    result.raw_responses.append({"simple_question": r.json() if r.status_code == 200 else r.text})
    check(result, "Simple question returns 200", r.status_code == 200)
    if r.status_code == 200:
        body = r.json()
        check(result, "Response has message field", "message" in body)
        check(result, "No tool calls for simple question", body.get("tool_calls", 0) == 0 or len(body.get("tool_calls", [])) == 0)

    # Tool-using question (calculator)
    r = api(client, "POST", "/v1/chat", json_body={"message": "Calculate 2^10 + sqrt(144)"})
    result.raw_responses.append({"tool_question": r.json() if r.status_code == 200 else r.text})
    check(result, "Tool question returns 200", r.status_code == 200)
    if r.status_code == 200:
        body = r.json()
        check(result, "Response includes tool_calls", "tool_calls" in body)
        check(result, "Response includes iterations", "iterations" in body)

    result.duration_ms = (time.time() - t0) * 1000
    return result


def lab_2_tool_exploration(client: httpx.Client) -> LabResult:
    """Lab 2: Tool Exploration — calculator, database, web search, list tools."""
    result = LabResult(lab=2, name="tool-exploration")
    t0 = time.time()

    # Calculator
    r = api(client, "POST", "/v1/chat", json_body={"message": "What is (15 * 24) + sqrt(625)?"})
    result.raw_responses.append({"calculator": r.json() if r.status_code == 200 else r.text})
    check(result, "Calculator request returns 200", r.status_code == 200)

    # Database query
    r = api(client, "POST", "/v1/chat", json_body={"message": "What are the top 3 most expensive products in the database?"})
    result.raw_responses.append({"database": r.json() if r.status_code == 200 else r.text})
    check(result, "Database query returns 200", r.status_code == 200)

    # Web search
    r = api(client, "POST", "/v1/chat", json_body={"message": "Search the web for latest AI news"})
    result.raw_responses.append({"web_search": r.json() if r.status_code == 200 else r.text})
    check(result, "Web search returns 200", r.status_code == 200)

    # List tools
    r = api(client, "GET", "/v1/tools")
    result.raw_responses.append({"tools_list": r.json() if r.status_code == 200 else r.text})
    check(result, "Tools endpoint returns 200", r.status_code == 200)
    if r.status_code == 200:
        tools = r.json()
        tool_list = tools if isinstance(tools, list) else tools.get("tools", [])
        check(result, "At least 3 tools available", len(tool_list) >= 3)

    result.duration_ms = (time.time() - t0) * 1000
    return result


def lab_3_conversation_continuity(client: httpx.Client) -> LabResult:
    """Lab 3: Conversation Continuity — multi-turn memory, CRUD."""
    result = LabResult(lab=3, name="conversation-continuity")
    t0 = time.time()

    # Start conversation
    r = api(client, "POST", "/v1/chat", json_body={"message": "My name is Alice and I work at Acme Corp."})
    result.raw_responses.append({"start": r.json() if r.status_code == 200 else r.text})
    check(result, "Start conversation returns 200", r.status_code == 200)

    conv_id = None
    if r.status_code == 200:
        body = r.json()
        conv_id = body.get("conversation_id")
        check(result, "Response includes conversation_id", conv_id is not None)

    # Continue (agent should remember)
    if conv_id:
        r = api(client, "POST", "/v1/chat", json_body={
            "message": "What is my name and where do I work?",
            "conversation_id": conv_id,
        })
        result.raw_responses.append({"continue": r.json() if r.status_code == 200 else r.text})
        check(result, "Continue conversation returns 200", r.status_code == 200)
        if r.status_code == 200:
            msg = r.json().get("message", "").lower()
            check(result, "Agent remembers name (Ketan)", "ketan" in msg)

    # List conversations
    r = api(client, "GET", "/v1/conversations")
    result.raw_responses.append({"list": r.json() if r.status_code == 200 else r.text})
    check(result, "List conversations returns 200", r.status_code == 200)

    # Get conversation detail
    if conv_id:
        r = api(client, "GET", f"/v1/conversations/{conv_id}")
        result.raw_responses.append({"detail": r.json() if r.status_code == 200 else r.text})
        check(result, "Conversation detail returns 200", r.status_code == 200)

    # Delete conversation
    if conv_id:
        r = api(client, "DELETE", f"/v1/conversations/{conv_id}")
        result.raw_responses.append({"delete": r.status_code})
        check(result, "Delete conversation returns 200", r.status_code == 200)

    result.duration_ms = (time.time() - t0) * 1000
    return result


def lab_4_health_check(client: httpx.Client) -> LabResult:
    """Lab 4: Health Check and Monitoring."""
    result = LabResult(lab=4, name="health-check")
    t0 = time.time()

    r = api(client, "GET", "/health")
    result.raw_responses.append({"health": r.json() if r.status_code == 200 else r.text})
    check(result, "Health endpoint returns 200", r.status_code == 200)
    if r.status_code == 200:
        body = r.json()
        check(result, "Status is healthy", body.get("status") == "healthy")
        components = body.get("components", {})
        check(result, "Has llm_provider component", "llm_provider" in components)
        check(result, "Has tools component", "tools" in components or "tool_names" in components)
        check(result, "Has agent_graph component", "agent_graph" in components)

    result.duration_ms = (time.time() - t0) * 1000
    return result


def lab_5_sse_streaming(client: httpx.Client) -> LabResult:
    """Lab 5: SSE Streaming — non-streaming vs streaming responses."""
    result = LabResult(lab=5, name="sse-streaming")
    t0 = time.time()

    # Non-streaming
    r = api(client, "POST", "/v1/chat", json_body={
        "message": "Explain how binary search works",
        "stream": False,
    })
    result.raw_responses.append({"non_streaming": r.json() if r.status_code == 200 else r.text})
    check(result, "Non-streaming returns 200", r.status_code == 200)
    if r.status_code == 200:
        check(result, "Response has latency_ms", "latency_ms" in r.json())

    # Streaming (collect SSE events)
    base_url = str(client.base_url).rstrip("/")
    stream_json = {"message": "What is 2+2?"}
    for _attempt in range(3):
        try:
            with client.stream("POST", "/v1/chat/stream", json=stream_json) as stream:
                events: list[str] = []
                for line in stream.iter_lines():
                    if line.startswith("data:"):
                        events.append(line)
                    if len(events) > 20:
                        break
                result.raw_responses.append({"streaming_events": len(events)})
                check(result, "Streaming returns SSE events", len(events) > 0)
            break
        except Exception as e:
            if _is_connection_error(e) and _attempt < 2:
                if _wait_for_server(base_url, context=f"lab_5 streaming, attempt {_attempt + 1}"):
                    continue
            result.raw_responses.append({"streaming_error": str(e)})
            check(result, "Streaming returns SSE events", False, notes=str(e))
            break

    result.duration_ms = (time.time() - t0) * 1000
    return result


def lab_6_multi_tool_chains(client: httpx.Client) -> LabResult:
    """Lab 6: Multi-Tool Chains — sequential tool use."""
    result = LabResult(lab=6, name="multi-tool-chains")
    t0 = time.time()

    # Multi-tool query
    r = api(client, "POST", "/v1/chat", json_body={
        "message": "Find the cheapest product in the database and calculate a 20% discount on it",
    })
    result.raw_responses.append({"multi_tool": r.json() if r.status_code == 200 else r.text})
    check(result, "Multi-tool request returns 200", r.status_code == 200)
    if r.status_code == 200:
        body = r.json()
        tool_calls = body.get("tool_calls", [])
        check(result, "Multiple tool calls made", len(tool_calls) >= 2 if isinstance(tool_calls, list) else False)
        check(result, "Iterations > 1", body.get("iterations", 0) > 1)

    # Tools disabled
    r = api(client, "POST", "/v1/chat", json_body={
        "message": "Calculate 2+2",
        "tools_enabled": False,
    })
    result.raw_responses.append({"tools_disabled": r.json() if r.status_code == 200 else r.text})
    check(result, "Tools-disabled returns 200", r.status_code == 200)
    if r.status_code == 200:
        body = r.json()
        tool_calls = body.get("tool_calls", [])
        check(result, "No tool calls when disabled", len(tool_calls) == 0 if isinstance(tool_calls, list) else tool_calls == 0)

    result.duration_ms = (time.time() - t0) * 1000
    return result


def lab_7_provider_switching(client: httpx.Client) -> LabResult:
    """Lab 7: Provider Switching — verify current provider from health check."""
    result = LabResult(lab=7, name="provider-switching")
    t0 = time.time()

    r = api(client, "GET", "/health")
    result.raw_responses.append({"health": r.json() if r.status_code == 200 else r.text})
    check(result, "Health endpoint returns 200", r.status_code == 200)
    if r.status_code == 200:
        body = r.json()
        provider = body.get("provider") or body.get("components", {}).get("llm_provider", "")
        check(result, "Provider field present", bool(provider))
        check(result, "Provider is valid", any(p in str(provider).lower() for p in ["local", "aws", "azure", "ollama", "bedrock"]))

    result.duration_ms = (time.time() - t0) * 1000
    return result


def lab_8_docker_deployment(client: httpx.Client) -> LabResult:
    """Lab 8: Docker Deployment — health check + conversation from container."""
    result = LabResult(lab=8, name="docker-deployment")
    t0 = time.time()

    # Health
    r = api(client, "GET", "/health")
    result.raw_responses.append({"health": r.json() if r.status_code == 200 else r.text})
    check(result, "Container health check returns 200", r.status_code == 200)

    # Conversation through container
    r = api(client, "POST", "/v1/chat", json_body={"message": "Hello, remember the number 42"})
    result.raw_responses.append({"chat": r.json() if r.status_code == 200 else r.text})
    check(result, "Chat through container returns 200", r.status_code == 200)
    if r.status_code == 200:
        conv_id = r.json().get("conversation_id")
        if conv_id:
            r2 = api(client, "POST", "/v1/chat", json_body={
                "message": "What number did I ask you to remember?",
                "conversation_id": conv_id,
            })
            result.raw_responses.append({"recall": r2.json() if r2.status_code == 200 else r2.text})
            check(result, "Recall through container returns 200", r2.status_code == 200)
            if r2.status_code == 200:
                check(result, "Agent recalls number 42", "42" in r2.json().get("message", ""))

    result.duration_ms = (time.time() - t0) * 1000
    return result


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
ALL_LABS: dict[int, callable] = {
    1: lab_1_first_interaction,
    2: lab_2_tool_exploration,
    3: lab_3_conversation_continuity,
    4: lab_4_health_check,
    5: lab_5_sse_streaming,
    6: lab_6_multi_tool_chains,
    7: lab_7_provider_switching,
    8: lab_8_docker_deployment,
}


def run_labs(base_url: str, env: str, only: list[int] | None = None, dry_run: bool = False) -> None:
    labs_to_run = {k: v for k, v in ALL_LABS.items() if only is None or k in only}

    print(f"\nAI Agent — Running {len(labs_to_run)} labs against {env} ({base_url})\n")

    if dry_run:
        for num, fn in labs_to_run.items():
            print(f"  [DRY RUN] Lab {num}: {fn.__doc__.strip().split(chr(10))[0] if fn.__doc__ else fn.__name__}")
        return

    passed = 0
    failed = 0

    with httpx.Client(base_url=base_url, timeout=60.0, headers={"Content-Type": "application/json"}) as client:
        for num, fn in labs_to_run.items():
            try:
                result = fn(client)
                save_result(result, env)
                if result.passed:
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"  Lab {num}: ERROR — {e}")
                failed += 1
                if _is_connection_error(e):
                    _wait_for_server(base_url, context=f"lab {num} failure")

    print(f"\nResults: {passed} passed, {failed} failed")
    print(f"Details: {RESULTS_DIR / env}/")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AI Agent hands-on labs")
    parser.add_argument("--env", choices=["local", "aws", "azure"], default="local")
    parser.add_argument("--only", nargs="+", type=int, help="Run only specific lab numbers")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing")
    parser.add_argument("--base-url", help="Override base URL")
    args = parser.parse_args()

    base_url = args.base_url or BASE_URLS[args.env]
    run_labs(base_url, args.env, args.only, args.dry_run)


if __name__ == "__main__":
    main()
