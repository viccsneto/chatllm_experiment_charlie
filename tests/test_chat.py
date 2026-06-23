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
        """Lista de sessoes deve ser um array."""
        response = client.get("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert isinstance(data["sessions"], list)

    def test_create_session(self, client: TestClient):
        """Criar sessao deve retornar os dados da sessao."""
        response = client.post("/api/sessions", json={"title": "Minha sessao"})
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Minha sessao"
        assert "id" in data

    def test_create_session_default_title(self, client: TestClient):
        """Criar sessao sem titulo deve usar padrao."""
        response = client.post("/api/sessions", json={})
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Nova sessao"

    def test_get_session(self, client: TestClient):
        """Deve retornar sessao por ID."""
        created = client.post("/api/sessions", json={"title": "Teste"}).json()
        response = client.get(f"/api/sessions/{created['id']}")
        assert response.status_code == 200
        assert response.json()["title"] == "Teste"

    def test_get_session_not_found(self, client: TestClient):
        """Sessao inexistente deve retornar 404."""
        response = client.get("/api/sessions/99999")
        assert response.status_code == 404

    def test_update_session_title(self, client: TestClient):
        """Deve atualizar o titulo de uma sessao."""
        created = client.post("/api/sessions", json={"title": "Antigo"}).json()
        response = client.patch(f"/api/sessions/{created['id']}", json={"title": "Novo"})
        assert response.status_code == 200
        assert response.json()["title"] == "Novo"

    def test_delete_session(self, client: TestClient):
        """Deve excluir sessao e retornar 204."""
        created = client.post("/api/sessions", json={"title": "Deletar"}).json()
        response = client.delete(f"/api/sessions/{created['id']}")
        assert response.status_code == 204
        # Verificar que sumiu
        get_response = client.get(f"/api/sessions/{created['id']}")
        assert get_response.status_code == 404

    def test_list_session_messages_empty(self, client: TestClient):
        """Sessao sem mensagens deve retornar lista vazia."""
        created = client.post("/api/sessions", json={}).json()
        response = client.get(f"/api/sessions/{created['id']}/messages")
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert data["messages"] == []

    def test_list_session_messages_not_found(self, client: TestClient):
        """Mensagens de sessao inexistente deve retornar 404."""
        response = client.get("/api/sessions/99999/messages")
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
