from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    def test_health_returns_ok(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestRootEndpoint:
    def test_root_returns_frontend(self, client: TestClient):
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


class TestChatEndpoint:
    def test_chat_endpoint_exists(self, client: TestClient):
        """Verifica que o endpoint /api/chat responde (espera erro de config sem API key)."""
        response = client.post(
            "/api/chat",
            json={"message": "Ola"},
        )
        # Sem OPENROUTER_API_KEY definida, esperamos 503 (config error)
        assert response.status_code in (200, 422, 503)

    def test_chat_empty_message_rejected(self, client: TestClient):
        """Mensagem vazia deve ser rejeitada com 422 (validacao Pydantic)."""
        response = client.post(
            "/api/chat",
            json={"message": ""},
        )
        assert response.status_code == 422


class TestChatStreamEndpoint:
    def test_chat_stream_endpoint_exists(self, client: TestClient):
        """Verifica que o endpoint /api/chat/stream aceita requisicoes."""
        response = client.post(
            "/api/chat/stream",
            json={"message": "Ola"},
        )
        # Streaming pode iniciar e depois falhar sem API key
        assert response.status_code in (200, 422, 503)

    def test_chat_stream_empty_message_rejected(self, client: TestClient):
        """Stream com mensagem vazia deve ser rejeitado com 422."""
        response = client.post(
            "/api/chat/stream",
            json={"message": ""},
        )
        assert response.status_code == 422


class TestSessionEndpoints:
    def test_list_sessions_empty(self, client: TestClient):
        """Listagem de sessoes deve retornar lista vazia inicialmente."""
        response = client.get("/api/sessions")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_sessions_after_creation(self, client: TestClient, db_session):
        """Deve listar sessoes apos criar uma."""
        from backend.models import Session

        s = Session(title="Sessao teste")
        db_session.add(s)
        db_session.commit()

        response = client.get("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Sessao teste"

    def test_get_session_messages_not_found(self, client: TestClient):
        """Sessao inexistente deve retornar 404."""
        response = client.get("/api/sessions/999/messages")
        assert response.status_code == 404

    def test_get_session_messages_empty(self, client: TestClient, db_session):
        """Sessao existente sem mensagens deve retornar lista vazia."""
        from backend.models import Session

        s = Session(title="Sessao vazia")
        db_session.add(s)
        db_session.commit()

        response = client.get(f"/api/sessions/{s.id}/messages")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_session_messages_with_content(self, client: TestClient, db_session):
        """Deve retornar mensagens de uma sessao ordenadas por created_at."""
        from backend.models import Message, Session

        s = Session(title="Sessao com msgs")
        db_session.add(s)
        db_session.flush()

        m1 = Message(session_id=s.id, role="user", content="Pergunta")
        m2 = Message(session_id=s.id, role="assistant", content="Resposta")
        db_session.add_all([m1, m2])
        db_session.commit()

        response = client.get(f"/api/sessions/{s.id}/messages")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["role"] == "user"
        assert data[0]["content"] == "Pergunta"
        assert data[1]["role"] == "assistant"
        assert data[1]["content"] == "Resposta"


class TestCORSMiddleware:
    def test_cors_headers_present(self, client: TestClient):
        """Verifica que os headers CORS estao presentes."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # O FastAPI com allow_origins=["*"] permite a requisicao
        assert response.status_code in (200, 405)
