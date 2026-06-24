from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import ChatMessage, Session as SessionModel, User
from backend.routers.auth import get_current_user
from backend.schemas.chat import (
    ChatMessageIn,
    SessionCreateOut,
    SessionListOut,
    SessionMessagesOut,
    SessionOut,
)


router = APIRouter()


@router.get("/api/sessions", response_model=SessionListOut)
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
) -> SessionListOut:
    query = db.query(SessionModel)
    if current_user:
        query = query.filter(SessionModel.user_id == current_user.id)
    else:
        query = query.filter(SessionModel.user_id.is_(None))
    sessions = query.order_by(SessionModel.updated_at.desc()).all()
    return SessionListOut(
        sessions=[SessionOut.model_validate(s) for s in sessions]
    )


@router.post("/api/sessions", response_model=SessionCreateOut, status_code=201)
def create_session(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
) -> SessionCreateOut:
    session = SessionModel(user_id=current_user.id if current_user else None)
    db.add(session)
    db.commit()
    db.refresh(session)
    return SessionCreateOut.model_validate(session)


@router.get("/api/sessions/{session_id}", response_model=SessionOut)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
) -> SessionOut:
    query = db.query(SessionModel).filter(SessionModel.id == session_id)
    if current_user:
        query = query.filter(SessionModel.user_id == current_user.id)
    else:
        query = query.filter(SessionModel.user_id.is_(None))
    session = query.first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")
    return SessionOut.model_validate(session)


@router.get("/api/sessions/{session_id}/messages", response_model=SessionMessagesOut)
def get_session_messages(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
) -> SessionMessagesOut:
    query = db.query(SessionModel).filter(SessionModel.id == session_id)
    if current_user:
        query = query.filter(SessionModel.user_id == current_user.id)
    else:
        query = query.filter(SessionModel.user_id.is_(None))
    session = query.first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    return SessionMessagesOut(
        session_id=session_id,
        messages=[
            ChatMessageIn(role=m.role, content=m.content) for m in messages
        ],
    )


@router.delete("/api/sessions/{session_id}", status_code=204)
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    query = db.query(SessionModel).filter(SessionModel.id == session_id)
    if current_user:
        query = query.filter(SessionModel.user_id == current_user.id)
    else:
        query = query.filter(SessionModel.user_id.is_(None))
    session = query.first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")
    db.delete(session)
    db.commit()