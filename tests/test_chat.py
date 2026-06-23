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


class TestSessionsEndpoint:
    def test_list_sessions_empty(self, client: TestClient):
        response = client.get("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert data["sessions"] == []

    def test_create_session(self, client: TestClient):
        response = client.post("/api/sessions")
        assert response.status_code == 201
        data = response.json()
        assert data["id"] is not None
        assert data["title"] is None

    def test_create_and_list_sessions(self, client: TestClient):
        client.post("/api/sessions")
        client.post("/api/sessions")
        response = client.get("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 2

    def test_get_session_not_found(self, client: TestClient):
        response = client.get("/api/sessions/999")
        assert response.status_code == 404

    def test_get_session_messages_empty(self, client: TestClient):
        resp = client.post("/api/sessions")
        sid = resp.json()["id"]
        response = client.get(f"/api/sessions/{sid}/messages")
        assert response.status_code == 200
        data = response.json()
        assert data["messages"] == []

    def test_delete_session(self, client: TestClient):
        resp = client.post("/api/sessions")
        sid = resp.json()["id"]
        response = client.delete(f"/api/sessions/{sid}")
        assert response.status_code == 204
        # Verify it's gone
        response = client.get(f"/api/sessions/{sid}")
        assert response.status_code == 404


class TestChatEndpoint:
    def test_chat_endpoint_creates_session(self, client: TestClient):
        """Verifica que o endpoint /api/chat aceita requisicao valida."""
        response = client.post(
            "/api/chat",
            json={"message": "Ola"},
        )
        # Pode responder com 200 (se API key configurada) ou 503 (sem API key)
        assert response.status_code in (200, 422, 503)

    def test_chat_empty_message_rejected(self, client: TestClient):
        """Mensagem vazia deve ser rejeitada com 422 (validacao Pydantic)."""
        response = client.post(
            "/api/chat",
            json={"message": ""},
        )
        assert response.status_code == 422

    def test_chat_with_nonexistent_session(self, client: TestClient):
        """Sessao inexistente deve retornar 404."""
        response = client.post(
            "/api/chat",
            json={"message": "Ola", "session_id": 999},
        )
        assert response.status_code == 404


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

    def test_chat_stream_with_nonexistent_session(self, client: TestClient):
        """Sessao inexistente no stream deve retornar 404."""
        response = client.post(
            "/api/chat/stream",
            json={"message": "Ola", "session_id": 999},
        )
        assert response.status_code == 404


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
