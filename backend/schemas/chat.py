from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatMessageIn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    model: str | None = None
    history: list[ChatMessageIn] = Field(default_factory=list)
    session_id: int | None = None


class ChatResponse(BaseModel):
    reply: str
    model: str
    session_id: int


class SessionOut(BaseModel):
    id: int
    title: str | None
    created_at: str
    updated_at: str


class SessionListOut(BaseModel):
    sessions: list[SessionOut]


class SessionCreateOut(BaseModel):
    id: int
    title: str | None


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    model: str
    created_at: str


class SessionMessagesOut(BaseModel):
    messages: list[MessageOut]
