from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from backend.database import get_db
from backend.models import Session, ChatMessage
from backend.routers.auth import get_current_user_id
from backend.schemas.chat import ChatMessageIn
from backend.schemas.session import SessionList, SessionOut, SessionRename
from backend.services.openrouter import generate_title
from pydantic import BaseModel


class SessionCreatePayload(BaseModel):
    session_key: str | None = None


router = APIRouter()


@router.get("/api/sessions", response_model=SessionList)
def list_sessions(
    db: DBSession = Depends(get_db),
    user_id: int | None = Depends(get_current_user_id),
):
    query = db.query(Session)
    if user_id:
        query = query.filter(Session.user_id == user_id)
    else:
        query = query.filter(Session.user_id.is_(None))
    sessions = query.order_by(Session.updated_at.desc()).all()
    return SessionList(sessions=sessions)


@router.post("/api/sessions", response_model=SessionOut, status_code=201)
def create_session(
    payload: SessionCreatePayload | None = None,
    db: DBSession = Depends(get_db),
    user_id: int | None = Depends(get_current_user_id),
):
    session_key = payload.session_key if (payload and payload.session_key) else uuid4().hex[:16]

    existing = db.query(Session).filter(Session.session_key == session_key).first()
    if existing:
        raise HTTPException(status_code=409, detail="Session key ja existe.")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    session = Session(
        session_key=session_key,
        user_id=user_id,
        title=None,
        created_at=now,
        updated_at=now,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/api/sessions/{session_key}", response_model=SessionOut)
def get_session(session_key: str, db: DBSession = Depends(get_db)):
    session = db.query(Session).filter(Session.session_key == session_key).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada.")
    return session


@router.patch("/api/sessions/{session_key}", response_model=SessionOut)
def rename_session(session_key: str, payload: SessionRename, db: DBSession = Depends(get_db)):
    session = db.query(Session).filter(Session.session_key == session_key).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada.")
    session.title = payload.title
    session.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(session)
    return session


@router.delete("/api/sessions/{session_key}", status_code=204)
def delete_session(session_key: str, db: DBSession = Depends(get_db)):
    session = db.query(Session).filter(Session.session_key == session_key).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada.")
    db.query(ChatMessage).filter(ChatMessage.session_key == session_key).delete()
    db.delete(session)
    db.commit()


@router.get("/api/sessions/{session_key}/messages")
def get_session_messages(session_key: str, db: DBSession = Depends(get_db)):
    session = db.query(Session).filter(Session.session_key == session_key).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada.")
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_key == session_key)
        .order_by(ChatMessage.created_at)
        .all()
    )
    return [
        {"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
        for m in messages
    ]