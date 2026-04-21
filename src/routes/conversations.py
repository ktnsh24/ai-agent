"""Conversation management routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from src.models import ConversationDetail, ConversationSummary

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/conversations", response_model=list[ConversationSummary])
async def list_conversations(request: Request) -> list[ConversationSummary]:
    """List all conversations."""
    store = request.app.state.conversation_store
    return await store.list_conversations()


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(request: Request, conversation_id: str) -> ConversationDetail:
    """Get a specific conversation with all messages."""
    store = request.app.state.conversation_store
    conversation = await store.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(request: Request, conversation_id: str) -> dict:
    """Delete a conversation."""
    store = request.app.state.conversation_store
    deleted = await store.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"deleted": True, "conversation_id": conversation_id}
