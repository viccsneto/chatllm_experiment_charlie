from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.config import OPENROUTER_MODEL_DEFAULT
from backend.database import SessionLocal, get_db
from backend.models import ChatMessage, Session as ChatSession
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.routers.auth import get_current_user_id
from backend.services.openrouter import OpenRouterConfigError, generate_reply, generate_title, stream_reply


router = APIRouter()


def _resolve_session(payload: ChatRequest, db: Session, user_id: int | None = None) -> ChatSession:
    """Get or auto-create a session for this request."""
    session_key = payload.session_key
    if session_key:
        session = db.query(ChatSession).filter(ChatSession.session_key == session_key).first()
        if session:
            session.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            db.commit()
            return session
    # Create new session
    session_key = uuid4().hex[:16]
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    session = ChatSession(session_key=session_key, user_id=user_id, title=None, created_at=now, updated_at=now)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


async def _try_set_title(session_key: str, db: Session | None = None):
    """Auto-generate title from conversation context if session has no title yet."""
    own_db = db is None
    if own_db:
        db = SessionLocal()
    try:
        session = db.query(ChatSession).filter(ChatSession.session_key == session_key).first()
        if not session or session.title is not None:
            return
        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_key == session_key)
            .order_by(ChatMessage.created_at)
            .limit(20)
            .all()
        )
        if len(messages) < 2:
            return
        conversation = [{"role": m.role, "content": m.content} for m in messages]
        try:
            title = await generate_title(conversation=conversation)
        except Exception:
            title = "Nova sessao"
        session.title = title
        session.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
    finally:
        if own_db:
            db.close()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: Session = Depends(get_db), user_id: int | None = Depends(get_current_user_id)) -> ChatResponse:
    # Resolve session
    session = _resolve_session(payload, db, user_id)
    session_key = session.session_key

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

    db.add(ChatMessage(session_key=session_key, role="user", content=payload.message, model=resolved_model))
    db.add(ChatMessage(session_key=session_key, role="assistant", content=reply, model=resolved_model))
    db.commit()

    await _try_set_title(session_key, db)

    return ChatResponse(reply=reply, model=resolved_model, session_key=session_key)


@router.post("/api/chat/stream")
async def chat_stream(payload: ChatRequest, db: Session = Depends(get_db), user_id: int | None = Depends(get_current_user_id)) -> StreamingResponse:
    resolved_model = payload.model or OPENROUTER_MODEL_DEFAULT
    session = _resolve_session(payload, db, user_id)
    session_key = session.session_key

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
            # Use a fresh db session inside the generator
            stream_db = SessionLocal()
            try:
                stream_db.add(
                    ChatMessage(
                        session_key=session_key,
                        role="user",
                        content=payload.message,
                        model=resolved_model,
                    )
                )
                stream_db.add(
                    ChatMessage(
                        session_key=session_key,
                        role="assistant",
                        content=full_reply,
                        model=resolved_model,
                    )
                )
                stream_db.commit()

                await _try_set_title(session_key, stream_db)
            finally:
                stream_db.close()

        yield f"data: {json.dumps({'done': True, 'session_key': session_key}, ensure_ascii=True)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
