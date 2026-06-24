from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.config import OPENROUTER_MODEL_DEFAULT
from backend.database import get_db
from backend.models import ChatMessage, ChatSession
from backend.schemas.chat import (
    ChatRequest,
    ChatResponse,
    MessageOut,
    SessionCreateIn,
    SessionListOut,
    SessionMessagesOut,
    SessionOut,
    SessionUpdateIn,
)
from backend.services.openrouter import (
    OpenRouterConfigError,
    generate_reply,
    generate_title_from_context,
    stream_reply,
)


router = APIRouter()


async def _generate_title(user_message: str) -> str:
    """Generate a short contextual title via LLM, fallback to user message snippet."""
    title = await generate_title_from_context(user_message)
    if title and title != "Nova sessao":
        return title
    # Fallback: first sentence of user message
    clean = user_message.strip().replace("\n", " ")
    first_period = clean.find(". ")
    if 10 < first_period < 80:
        clean = clean[: first_period + 1]
    return clean[:80].strip() or "Nova sessao"


def _get_session(db: Session, session_id: int | None) -> ChatSession | None:
    """Get an existing session or return None. Never creates one."""
    if session_id is None:
        return None
    return db.query(ChatSession).filter(ChatSession.id == session_id).first()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


# ─── Session CRUD ────────────────────────────────────────────────────────────


@router.get("/api/sessions", response_model=SessionListOut)
def list_sessions(db: Session = Depends(get_db)):
    sessions = (
        db.query(ChatSession)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    return SessionListOut(sessions=sessions)


@router.post("/api/sessions", response_model=SessionOut, status_code=201)
def create_session(payload: SessionCreateIn, db: Session = Depends(get_db)):
    session = ChatSession(title=payload.title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/api/sessions/{session_id}", response_model=SessionOut)
def get_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")
    return session


@router.patch("/api/sessions/{session_id}", response_model=SessionOut)
def update_session(session_id: int, payload: SessionUpdateIn, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")
    session.title = payload.title
    db.commit()
    db.refresh(session)
    return session


@router.delete("/api/sessions/{session_id}", status_code=204)
def delete_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")
    db.delete(session)
    db.commit()


@router.get("/api/sessions/{session_id}/messages", response_model=SessionMessagesOut)
def list_session_messages(session_id: int, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return SessionMessagesOut(messages=messages)


# ─── Chat ────────────────────────────────────────────────────────────────────


@router.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
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

    # Get existing session or create a new one only after successful reply
    session = _get_session(db, payload.session_id)
    if session is None:
        title = await _generate_title(payload.message)
        session = ChatSession(title=title)
        db.add(session)
        db.flush()

    db.add(ChatMessage(session_id=session.id, role="user", content=payload.message, model=resolved_model))
    db.add(ChatMessage(session_id=session.id, role="assistant", content=reply, model=resolved_model))
    db.commit()

    return ChatResponse(reply=reply, model=resolved_model, session_id=session.id)


@router.post("/api/chat/stream")
async def chat_stream(payload: ChatRequest, db: Session = Depends(get_db)) -> StreamingResponse:
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
            # Get existing session or create a new one only after reply is complete
            session = _get_session(db, payload.session_id)
            if session is None:
                title = await _generate_title(payload.message)
                session = ChatSession(title=title)
                db.add(session)
                db.flush()

            db.add(
                ChatMessage(
                    session_id=session.id,
                    role="user",
                    content=payload.message,
                    model=resolved_model,
                )
            )
            db.add(
                ChatMessage(
                    session_id=session.id,
                    role="assistant",
                    content=full_reply,
                    model=resolved_model,
                )
            )
            db.commit()

            session_id = session.id
        else:
            session_id = payload.session_id

        yield f"data: {json.dumps({'done': True, 'session_id': session_id}, ensure_ascii=True)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
