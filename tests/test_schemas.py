from __future__ import annotations

import pytest
from pydantic import ValidationError

from datetime import datetime

from pydantic import ValidationError

from backend.schemas.chat import (
    ChatMessageIn,
    ChatRequest,
    ChatResponse,
    MessageOut,
    SessionOut,
)


class TestChatMessageIn:
    def test_valid_user_message(self):
        msg = ChatMessageIn(role="user", content="Ola!")
        assert msg.role == "user"
        assert msg.content == "Ola!"

    def test_valid_assistant_message(self):
        msg = ChatMessageIn(role="assistant", content="Resposta.")
        assert msg.role == "assistant"
        assert msg.content == "Resposta."

    def test_invalid_role(self):
        with pytest.raises(ValidationError):
            ChatMessageIn(role="system", content="Nao permitido")

    def test_empty_content(self):
        with pytest.raises(ValidationError):
            ChatMessageIn(role="user", content="")

    def test_content_too_long(self):
        with pytest.raises(ValidationError):
            ChatMessageIn(role="user", content="x" * 8001)


class TestChatRequest:
    def test_valid_request_minimal(self):
        req = ChatRequest(message="Hello")
        assert req.message == "Hello"
        assert req.model is None
        assert req.history == []

    def test_valid_request_with_model(self):
        req = ChatRequest(message="Hi", model="openai/gpt-4o")
        assert req.model == "openai/gpt-4o"

    def test_valid_request_with_session_id(self):
        req = ChatRequest(message="Hi", session_id=42)
        assert req.session_id == 42

    def test_valid_request_with_history(self):
        history = [
            ChatMessageIn(role="user", content="pergunta"),
            ChatMessageIn(role="assistant", content="resposta"),
        ]
        req = ChatRequest(message="continuacao", history=history)
        assert len(req.history) == 2
        assert req.history[0].role == "user"

    def test_empty_message(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="")

    def test_message_too_long(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="x" * 8001)

    def test_history_defaults_to_empty(self):
        req = ChatRequest(message="Hello")
        assert req.history == []


class TestChatResponse:
    def test_valid_response(self):
        resp = ChatResponse(
            reply="Resposta do modelo.",
            model="google/gemma-4-31b-it",
            session_id=1,
        )
        assert resp.reply == "Resposta do modelo."
        assert resp.model == "google/gemma-4-31b-it"
        assert resp.session_id == 1


class TestSessionOut:
    def test_valid_session_out(self):
        now = datetime.now()
        s = SessionOut(id=1, title="Teste", created_at=now, updated_at=now)
        assert s.id == 1
        assert s.title == "Teste"

    def test_session_out_from_attributes(self):
        """Simula criacao a partir de atributos ORM."""
        now = datetime.now()
        s = SessionOut.model_validate(
            {"id": 5, "title": "ORM Session", "created_at": now, "updated_at": now}
        )
        assert s.id == 5
        assert s.title == "ORM Session"


class TestMessageOut:
    def test_valid_message_out(self):
        now = datetime.now()
        m = MessageOut(
            id=1,
            session_id=1,
            role="user",
            content="Oi",
            model="google/gemma-4-31b-it",
            created_at=now,
        )
        assert m.role == "user"
        assert m.content == "Oi"

    def test_message_out_from_attributes(self):
        now = datetime.now()
        m = MessageOut.model_validate(
            {
                "id": 2,
                "session_id": 1,
                "role": "assistant",
                "content": "Resposta",
                "model": "google/gemma-4-31b-it",
                "created_at": now,
            }
        )
        assert m.role == "assistant"
        assert m.content == "Resposta"
