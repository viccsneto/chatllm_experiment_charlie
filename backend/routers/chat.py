from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.config import OPENROUTER_MODEL_DEFAULT
from backend.database import get_db
from backend.models import ChatMessage, Message, Session, User
from backend.routers.auth import get_current_user
from backend.schemas.chat import (
    ChatMessageIn,
    ChatRequest,
    ChatResponse,
    MessageOut,
    SessionOut,
)
from backend.services.openrouter import OpenRouterConfigError, generate_reply, stream_reply


router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


def _get_or_create_session(
    db: Session,
    session_id: int | None,
    user_message: str,
    user_id: int,
) -> Session:
    if session_id is not None:
        session = (
            db.query(Session)
            .filter(Session.id == session_id, Session.user_id == user_id)
            .first()
        )
        if not session:
            raise HTTPException(status_code=404, detail="Sessao nao encontrada")
        session.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        return session

    title = user_message[:60] + ("..." if len(user_message) > 60 else "")
    session = Session(title=title, user_id=user_id)
    db.add(session)
    db.flush()
    return session


def _persist_messages(
    db: Session,
    session_id: int,
    user_message: str,
    reply: str,
    model: str,
) -> None:
    db.add(
        Message(session_id=session_id, role="user", content=user_message, model=model)
    )
    db.add(
        Message(
            session_id=session_id,
            role="assistant",
            content=reply,
            model=model,
        )
    )
    db.commit()


@router.post("/api/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    session = _get_or_create_session(db, payload.session_id, payload.message, current_user.id)

    try:
        reply, model_name = await generate_reply(
            user_message=payload.message,
            history=[item.model_dump() for item in payload.history],
            model=payload.model,
        )
    except OpenRouterConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    resolved_model = payload.model or model_name or OPENROUTER_MODEL_DEFAULT

    db.add(
        ChatMessage(
            session_key="default",
            role="user",
            content=payload.message,
            model=resolved_model,
        )
    )
    db.add(
        ChatMessage(
            session_key="default",
            role="assistant",
            content=reply,
            model=resolved_model,
        )
    )

    _persist_messages(db, session.id, payload.message, reply, resolved_model)

    return ChatResponse(reply=reply, model=resolved_model, session_id=session.id)


@router.post("/api/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    resolved_model = payload.model or OPENROUTER_MODEL_DEFAULT

    async def event_generator():
        full_reply = ""
        try:
            async for delta in stream_reply(
                user_message=payload.message,
                history=[item.model_dump() for item in payload.history],
                model=payload.model,
            ):
                full_reply += delta
                yield f"data: {json.dumps({'delta': delta}, ensure_ascii=True)}\n\n"
        except OpenRouterConfigError as exc:
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=True)}\n\n"
            return
        except RuntimeError as exc:
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=True)}\n\n"
            return

        if full_reply.strip():
            session = _get_or_create_session(
                db, payload.session_id, payload.message, current_user.id
            )

            db.add(
                ChatMessage(
                    session_key="default",
                    role="user",
                    content=payload.message,
                    model=resolved_model,
                )
            )
            db.add(
                ChatMessage(
                    session_key="default",
                    role="assistant",
                    content=full_reply,
                    model=resolved_model,
                )
            )

            _persist_messages(
                db, session.id, payload.message, full_reply, resolved_model
            )

            yield f"data: {json.dumps({'done': True, 'session_id': session.id}, ensure_ascii=True)}\n\n"
        else:
            yield f"data: {json.dumps({'done': True}, ensure_ascii=True)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/api/sessions", response_model=list[SessionOut])
def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Session]:
    return (
        db.query(Session)
        .filter(Session.user_id == current_user.id)
        .order_by(Session.updated_at.desc())
        .all()
    )


@router.get("/api/sessions/{session_id}/messages", response_model=list[MessageOut])
def list_session_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Message]:
    session = (
        db.query(Session)
        .filter(Session.id == session_id, Session.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    return (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
        .all()
    )
