"""Chat endpoints — legacy parity."""

from __future__ import annotations

from fastapi import APIRouter, Header, Request

from infinite_canvas.schemas.chat import ChatRequest
from infinite_canvas.services import chat as chat_service

router = APIRouter(tags=["chat"])


@router.post("/api/chat")
async def chat(payload: ChatRequest, request: Request, x_user_id: str = Header(default="")):
    return await chat_service.chat_sync(payload, request, x_user_id)


@router.post("/api/chat/agent")
async def chat_agent(payload: ChatRequest, request: Request, x_user_id: str = Header(default="")):
    return await chat_service.chat_agent(payload, request, x_user_id)


@router.post("/api/chat/stream")
async def chat_stream(payload: ChatRequest, request: Request, x_user_id: str = Header(default="")):
    return await chat_service.chat_stream(payload, request, x_user_id)
