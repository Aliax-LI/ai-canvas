"""Conversation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Header, Request

from infinite_canvas.schemas.conversation import ConversationCreateRequest
from infinite_canvas.services import conversations as conversation_service

router = APIRouter(tags=["conversations"])


@router.get("/api/conversations")
async def conversations(request: Request, x_user_id: str = Header(default="")):
    user_id = conversation_service.safe_user_id(x_user_id, request)
    return {"user_id": user_id, "conversations": conversation_service.list_conversations(user_id)}


@router.post("/api/conversations")
async def create_conversation(
    payload: ConversationCreateRequest,
    request: Request,
    x_user_id: str = Header(default=""),
):
    user_id = conversation_service.safe_user_id(x_user_id, request)
    return {"conversation": conversation_service.new_conversation(user_id, payload.title)}


@router.get("/api/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    request: Request,
    x_user_id: str = Header(default=""),
):
    user_id = conversation_service.safe_user_id(x_user_id, request)
    return {"conversation": conversation_service.load_conversation(user_id, conversation_id)}


@router.delete("/api/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    request: Request,
    x_user_id: str = Header(default=""),
):
    user_id = conversation_service.safe_user_id(x_user_id, request)
    conversation_service.delete_conversation(user_id, conversation_id)
    return {"ok": True}
