"""Conversation request schemas."""

from __future__ import annotations

from pydantic import BaseModel


class ConversationCreateRequest(BaseModel):
    title: str = "新对话"
