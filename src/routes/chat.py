"""Chat route — main agent interaction endpoint."""

from __future__ import annotations

import json
import logging
import time

from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from src.models import AgentRequest, AgentResponse, AgentStatus

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat", response_model=AgentResponse)
async def chat(request: Request, body: AgentRequest) -> AgentResponse:
    """Send a message to the AI agent.

    The agent will:
    1. Analyse the message
    2. Decide whether to use tools
    3. Execute tool calls if needed
    4. Return a final response

    Supports conversation continuity via conversation_id.
    """
    agent_graph = request.app.state.agent_graph
    conversation_store = request.app.state.conversation_store

    # Get or create conversation
    conversation_id = body.conversation_id
    conversation_history = None

    if conversation_id:
        conversation_history = await conversation_store.get_messages(conversation_id)
        if not conversation_history:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conversation_id = await conversation_store.create_conversation(
            title=body.message[:50] if body.message else "New Conversation"
        )

    # Store user message
    await conversation_store.add_message(conversation_id, "user", body.message)

    # Run agent
    try:
        response = await agent_graph.run(
            user_message=body.message,
            conversation_history=conversation_history,
            max_iterations=body.max_iterations,
        )
    except Exception as e:
        logger.error("Agent execution failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    # Store assistant response
    await conversation_store.add_message(conversation_id, "assistant", response.message)

    # Override conversation_id with the actual one
    response.conversation_id = conversation_id

    return response


@router.post("/chat/stream")
async def chat_stream(request: Request, body: AgentRequest):
    """Stream agent responses via Server-Sent Events (SSE).

    Events:
    - thinking: Agent is processing
    - tool_call: Agent invoked a tool
    - token: A response token
    - done: Agent finished
    - error: An error occurred
    """
    agent_graph = request.app.state.agent_graph
    conversation_store = request.app.state.conversation_store

    conversation_id = body.conversation_id
    if not conversation_id:
        conversation_id = await conversation_store.create_conversation(
            title=body.message[:50] if body.message else "New Conversation"
        )

    await conversation_store.add_message(conversation_id, "user", body.message)

    async def event_generator():
        """Generate SSE events for the agent execution."""
        try:
            # Emit thinking event
            yield {
                "event": "thinking",
                "data": json.dumps({"conversation_id": conversation_id}),
            }

            # Run agent (non-streaming for now, emit full response)
            conversation_history = await conversation_store.get_messages(conversation_id)
            # Remove the message we just added (it's in the history now)
            if conversation_history:
                conversation_history = conversation_history[:-1]

            response = await agent_graph.run(
                user_message=body.message,
                conversation_history=conversation_history,
                max_iterations=body.max_iterations,
            )

            # Emit tool calls
            for tc in response.tool_calls:
                yield {
                    "event": "tool_call",
                    "data": json.dumps({
                        "name": tc.name,
                        "arguments": tc.arguments,
                        "result": tc.result,
                    }),
                }

            # Emit response tokens (simulated word-by-word for demo)
            words = response.message.split()
            for i, word in enumerate(words):
                yield {
                    "event": "token",
                    "data": word + (" " if i < len(words) - 1 else ""),
                }

            # Store assistant response
            await conversation_store.add_message(conversation_id, "assistant", response.message)

            # Emit done
            yield {
                "event": "done",
                "data": json.dumps({
                    "conversation_id": conversation_id,
                    "iterations": response.iterations,
                    "tool_calls": len(response.tool_calls),
                    "model": response.model,
                    "latency_ms": response.latency_ms,
                }),
            }

        except Exception as e:
            logger.error("Stream error: %s", e)
            yield {
                "event": "error",
                "data": json.dumps({"message": str(e)}),
            }

    return EventSourceResponse(event_generator())
