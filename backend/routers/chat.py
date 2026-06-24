from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.config import OPENROUTER_MODEL_DEFAULT
from backend.database import get_db
from backend.models import ChatMessage, Session as SessionModel, User
from backend.routers.auth import get_current_user
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.openrouter import OpenRouterConfigError, generate_reply, stream_reply


router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


def _get_or_create_session(db: Session, session_id: int | None, user_id: int | None) -> SessionModel:
    if session_id is not None:
        query = db.query(SessionModel).filter(SessionModel.id == session_id)
        if user_id:
            query = query.filter(SessionModel.user_id == user_id)
        else:
            query = query.filter(SessionModel.user_id.is_(None))
        session = query.first()
        if session:
            return session
    session = SessionModel(user_id=user_id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _maybe_set_session_title(db: Session, session: SessionModel, reply: str) -> str | None:
    """Define o titulo da sessao a partir da primeira resposta do modelo, se ainda nao houver titulo.

    Retorna o titulo definido ou None se ja existia.
    """
    if session.title:
        return session.title
    title = next((line.strip() for line in reply.split("\n") if line.strip()), reply)
    if len(title) > 60:
        title = title[:57] + "..."
    session.title = title
    return title


@router.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: Session = Depends(get_db), current_user: User | None = Depends(get_current_user)) -> ChatResponse:
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
    session = _get_or_create_session(db, payload.session_id, current_user.id if current_user else None)

    db.add(ChatMessage(session_id=session.id, role="user", content=payload.message, model=resolved_model))
    db.add(ChatMessage(session_id=session.id, role="assistant", content=reply, model=resolved_model))
    _maybe_set_session_title(db, session, reply)
    db.commit()
    db.refresh(session)

    return ChatResponse(reply=reply, model=resolved_model)


@router.post("/api/chat/stream")
async def chat_stream(payload: ChatRequest, db: Session = Depends(get_db), current_user: User | None = Depends(get_current_user)) -> StreamingResponse:
    resolved_model = payload.model or OPENROUTER_MODEL_DEFAULT
    session = _get_or_create_session(db, payload.session_id, current_user.id if current_user else None)

    async def event_generator():
        full_reply = ""
        # Busca sessao novamente dentro do generator para garantir objeto attached
        current_session = db.query(SessionModel).filter(SessionModel.id == session.id).first()
        if not current_session:
            current_session = session
        try:
            async for delta in stream_reply(
                user_message=payload.message,
                history=[item.model_dump() for item in payload.history],
                model=payload.model,
            ):
                full_reply += delta
                yield f"data: {json.dumps({'delta': delta, 'session_id': current_session.id}, ensure_ascii=True)}\n\n"
        except OpenRouterConfigError as exc:
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=True)}\n\n"
            return
        except RuntimeError as exc:
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=True)}\n\n"
            return

        if full_reply.strip():
            db.add(
                ChatMessage(
                    session_id=current_session.id,
                    role="user",
                    content=payload.message,
                    model=resolved_model,
                )
            )
            db.add(
                ChatMessage(
                    session_id=current_session.id,
                    role="assistant",
                    content=full_reply,
                    model=resolved_model,
                )
            )
            _maybe_set_session_title(db, current_session, full_reply)
            db.commit()
            db.refresh(current_session)

        yield f"data: {json.dumps({'done': True, 'session_id': current_session.id, 'session_title': current_session.title or None}, ensure_ascii=True)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
