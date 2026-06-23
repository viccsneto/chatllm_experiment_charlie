from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import ChatMessage, ChatSession, User
from backend.routers.auth import get_current_user
from backend.schemas.chat import (
    MessageOut,
    SessionCreateOut,
    SessionListOut,
    SessionMessagesOut,
    SessionOut,
)


router = APIRouter()


def _session_to_out(s: ChatSession) -> SessionOut:
    return SessionOut(
        id=s.id,
        title=s.title,
        created_at=s.created_at.isoformat(),
        updated_at=s.updated_at.isoformat(),
    )


def _message_to_out(m: ChatMessage) -> MessageOut:
    return MessageOut(
        id=m.id,
        role=m.role,
        content=m.content,
        model=m.model,
        created_at=m.created_at.isoformat(),
    )


@router.get("/api/sessions", response_model=SessionListOut)
def list_sessions(request: Request, db: Session = Depends(get_db)):
    user: User | None = get_current_user(request, db)
    query = db.query(ChatSession)
    if user is not None:
        query = query.filter(ChatSession.user_id == user.id)
    else:
        query = query.filter(ChatSession.user_id.is_(None))
    sessions = query.order_by(ChatSession.updated_at.desc()).all()
    return SessionListOut(sessions=[_session_to_out(s) for s in sessions])


@router.post("/api/sessions", response_model=SessionCreateOut, status_code=201)
def create_session(request: Request, db: Session = Depends(get_db)):
    user: User | None = get_current_user(request, db)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    session = ChatSession(
        title=None,
        user_id=user.id if user else None,
        created_at=now,
        updated_at=now,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return SessionCreateOut(id=session.id, title=session.title)


@router.get("/api/sessions/{session_id}", response_model=SessionOut)
def get_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")
    return _session_to_out(session)


@router.get("/api/sessions/{session_id}/messages", response_model=SessionMessagesOut)
def get_session_messages(session_id: int, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return SessionMessagesOut(messages=[_message_to_out(m) for m in messages])


@router.delete("/api/sessions/{session_id}", status_code=204)
def delete_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")
    db.delete(session)
    db.commit()