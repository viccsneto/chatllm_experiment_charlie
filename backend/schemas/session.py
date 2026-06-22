from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SessionOut(BaseModel):
    id: int
    session_key: str
    title: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SessionList(BaseModel):
    sessions: list[SessionOut]


class SessionCreate(BaseModel):
    session_key: str


class SessionRename(BaseModel):
    title: str