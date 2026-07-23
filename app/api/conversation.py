"""Conversation management endpoints.

Provides CRUD operations for conversations (used by notebook parent/chapter
pre-registration and general conversation lifecycle management).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.api.deps import get_container_from_request
from app.core.container import AppContainer
from app.core.exceptions import AppError
from app.schemas import ConversationCreateRequest, ConversationResponse

router = APIRouter()


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    req: ConversationCreateRequest,
    container: AppContainer = Depends(get_container_from_request),
) -> ConversationResponse:
    """Create a conversation (idempotent if conversation_id provided in meta)."""
    store = container.conversation_store
    conversation_id = req.meta.pop("_conversation_id", None) or f"conv_{uuid.uuid4().hex[:12]}"
    conv = store.create_conversation(
        conversation_id=conversation_id,
        type=req.type,
        title=req.title,
        parent_id=req.parent_id,
        module_key=req.module_key,
        meta=req.meta,
    )
    return _to_response(conv)


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    container: AppContainer = Depends(get_container_from_request),
) -> ConversationResponse:
    """Get conversation metadata by ID."""
    store = container.conversation_store
    conv = store.get_conversation(conversation_id)
    if conv is None:
        raise AppError(f"Conversation not found: {conversation_id}", status_code=404, code="NOT_FOUND")
    return _to_response(conv)


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    container: AppContainer = Depends(get_container_from_request),
) -> dict:
    """Delete a conversation and all its messages."""
    store = container.conversation_store
    deleted = store.delete_conversation(conversation_id)
    if not deleted:
        raise AppError(f"Conversation not found: {conversation_id}", status_code=404, code="NOT_FOUND")
    return {"status": "success", "deleted": True}


def _to_response(conv) -> ConversationResponse:
    """Convert Conversation dataclass to ConversationResponse."""
    return ConversationResponse(
        conversation_id=conv.conversation_id,
        type=conv.type,
        title=conv.title,
        parent_id=conv.parent_id,
        module_key=conv.module_key,
        summary=conv.summary,
        message_count=conv.message_count,
        created_at=conv.created_at,
    )
