from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.schemas.chat import (
    ChatMessageIn,
    ChatRequest,
    ChatResponse,
    MessageOut,
    SessionCreateOut,
    SessionListOut,
    SessionMessagesOut,
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
        assert req.session_id is None

    def test_valid_request_with_session_id(self):
        req = ChatRequest(message="Hi", session_id=42)
        assert req.session_id == 42

    def test_valid_request_with_model(self):
        req = ChatRequest(message="Hi", model="openai/gpt-4o")
        assert req.model == "openai/gpt-4o"

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
        resp = ChatResponse(reply="Resposta do modelo.", model="google/gemma-4-31b-it", session_id=1)
        assert resp.reply == "Resposta do modelo."
        assert resp.model == "google/gemma-4-31b-it"
        assert resp.session_id == 1


class TestSessionOut:
    def test_valid(self):
        s = SessionOut(id=1, title="Teste", created_at="2025-01-01T00:00:00", updated_at="2025-01-01T00:00:00")
        assert s.id == 1
        assert s.title == "Teste"


class TestSessionListOut:
    def test_valid(self):
        s = SessionOut(id=1, title="Teste", created_at="2025-01-01T00:00:00", updated_at="2025-01-01T00:00:00")
        sl = SessionListOut(sessions=[s])
        assert len(sl.sessions) == 1


class TestSessionCreateOut:
    def test_valid(self):
        s = SessionCreateOut(id=1, title=None)
        assert s.id == 1
        assert s.title is None


class TestMessageOut:
    def test_valid(self):
        m = MessageOut(id=1, role="user", content="msg", model="m", created_at="2025-01-01T00:00:00")
        assert m.role == "user"


class TestSessionMessagesOut:
    def test_valid(self):
        m = MessageOut(id=1, role="user", content="msg", model="m", created_at="2025-01-01T00:00:00")
        sm = SessionMessagesOut(messages=[m])
        assert len(sm.messages) == 1
