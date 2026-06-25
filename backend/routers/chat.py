from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.config import OPENROUTER_MODEL_DEFAULT
from backend.database import get_db
from backend.models import ChatMessage, ChatSession
from backend.schemas.chat import (
    ChatRequest,
    ChatResponse,
    SessionCreateResponse,
    SessionListResponse,
    SessionMessagesResponse,
    SessionSummary,
    SessionTitleUpdate,
)
from backend.services.openrouter import OpenRouterConfigError, generate_reply, stream_reply


router = APIRouter()

_TITLE_GENERATION_PROMPT = (
    "Gere um título curto (máximo 6 palavras, em português) para esta conversa. "
    "Responda APENAS com o título, sem aspas, sem pontuação extra."
)


def _get_or_create_session(db: Session, session_id: int | None) -> ChatSession:
    if session_id is not None:
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if session:
            return session
    session = ChatSession(title=None)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _ensure_session_title(db: Session, session: ChatSession, user_message: str):
    """Gera título automático para sessões sem título, usando a primeira mensagem do usuário."""
    if session.title is not None:
        return

    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Criar uma nova tarefa para gerar o título em background
        asyncio.ensure_future(_generate_title_async(db, session, user_message))
    else:
        asyncio.run(_generate_title_async(db, session, user_message))


async def _generate_title_async(db: Session, session: ChatSession, user_message: str):
    """Gera título chamando o modelo OpenRouter."""
    from backend.services.openrouter import OPENROUTER_API_KEY, OPENROUTER_MODEL_DEFAULT

    if not OPENROUTER_API_KEY:
        return

    prompt = f"{_TITLE_GENERATION_PROMPT}\n\nPrimeira mensagem: {user_message[:200]}"
    try:
        reply, _ = await generate_reply(
            user_message=prompt,
            history=[],
            model=OPENROUTER_MODEL_DEFAULT,
        )
        title = reply.strip().strip('"\'').strip()[:255]
        if title:
            session.title = title
            db.commit()
    except Exception:
        pass


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    session = _get_or_create_session(db, payload.session_id)

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

    session_key = str(uuid.uuid4())[:8]
    db.add(
        ChatMessage(
            session_key=session_key,
            session_id=session.id,
            role="user",
            content=payload.message,
            model=resolved_model,
        )
    )
    db.add(
        ChatMessage(
            session_key=session_key,
            session_id=session.id,
            role="assistant",
            content=reply,
            model=resolved_model,
        )
    )

    # Gerar título automático se for primeira mensagem da sessão
    msg_count = db.query(func.count(ChatMessage.id)).filter(
        ChatMessage.session_id == session.id
    ).scalar()
    if msg_count <= 2 and session.title is None:
        _ensure_session_title(db, session, payload.message)

    db.commit()

    return ChatResponse(reply=reply, model=resolved_model, session_id=session.id)


@router.post("/api/chat/stream")
async def chat_stream(payload: ChatRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    resolved_model = payload.model or OPENROUTER_MODEL_DEFAULT
    session = _get_or_create_session(db, payload.session_id)

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
            session_key = str(uuid.uuid4())[:8]
            db.add(
                ChatMessage(
                    session_key=session_key,
                    session_id=session.id,
                    role="user",
                    content=payload.message,
                    model=resolved_model,
                )
            )
            db.add(
                ChatMessage(
                    session_key=session_key,
                    session_id=session.id,
                    role="assistant",
                    content=full_reply,
                    model=resolved_model,
                )
            )

            msg_count = db.query(func.count(ChatMessage.id)).filter(
                ChatMessage.session_id == session.id
            ).scalar()
            if msg_count <= 2 and session.title is None:
                _ensure_session_title(db, session, payload.message)

            db.commit()

        yield f"data: {json.dumps({'done': True, 'session_id': session.id}, ensure_ascii=True)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# --- Session management endpoints ---


@router.get("/api/sessions", response_model=SessionListResponse)
def list_sessions(db: Session = Depends(get_db)):
    """Lista todas as sessões ordenadas pela mais recente."""
    sessions = (
        db.query(
            ChatSession.id,
            ChatSession.title,
            ChatSession.created_at,
            ChatSession.updated_at,
            func.count(ChatMessage.id).label("message_count"),
        )
        .outerjoin(ChatMessage, ChatMessage.session_id == ChatSession.id)
        .group_by(ChatSession.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )

    return SessionListResponse(
        sessions=[
            SessionSummary(
                id=s.id,
                title=s.title,
                message_count=s.message_count,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in sessions
        ]
    )


@router.post("/api/sessions", response_model=SessionCreateResponse, status_code=201)
def create_session(db: Session = Depends(get_db)):
    """Cria uma nova sessão vazia."""
    session = ChatSession(title=None)
    db.add(session)
    db.commit()
    db.refresh(session)
    return SessionCreateResponse(id=session.id, title=session.title)


@router.get("/api/sessions/{session_id}/messages", response_model=SessionMessagesResponse)
def get_session_messages(session_id: int, db: Session = Depends(get_db)):
    """Retorna as mensagens de uma sessão."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )

    return SessionMessagesResponse(
        session_id=session.id,
        title=session.title,
        messages=[
            {"role": m.role, "content": m.content} for m in messages
        ],
    )


@router.delete("/api/sessions/{session_id}", status_code=204)
def delete_session(session_id: int, db: Session = Depends(get_db)):
    """Remove uma sessão e todas as suas mensagens."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")
    db.delete(session)
    db.commit()


@router.patch("/api/sessions/{session_id}/title", response_model=SessionCreateResponse)
def update_session_title(session_id: int, payload: SessionTitleUpdate, db: Session = Depends(get_db)):
    """Atualiza o título de uma sessão."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")
    session.title = payload.title
    db.commit()
    db.refresh(session)
    return SessionCreateResponse(id=session.id, title=session.title)
