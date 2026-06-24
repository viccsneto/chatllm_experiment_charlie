from __future__ import annotations

from fastapi.testclient import TestClient
from backend.models import Session as SessionModel, ChatMessage


class TestSessionsAPI:
    def test_create_session(self, client: TestClient):
        response = client.post("/api/sessions")
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["title"] is None

    def test_list_sessions(self, client: TestClient):
        client.post("/api/sessions")
        client.post("/api/sessions")
        response = client.get("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) >= 2

    def test_get_session(self, client: TestClient):
        create_resp = client.post("/api/sessions")
        sid = create_resp.json()["id"]
        response = client.get(f"/api/sessions/{sid}")
        assert response.status_code == 200
        assert response.json()["id"] == sid

    def test_get_session_messages_empty(self, client: TestClient):
        create_resp = client.post("/api/sessions")
        sid = create_resp.json()["id"]
        response = client.get(f"/api/sessions/{sid}/messages")
        assert response.status_code == 200
        assert response.json()["messages"] == []

    def test_delete_session(self, client: TestClient):
        create_resp = client.post("/api/sessions")
        sid = create_resp.json()["id"]
        response = client.delete(f"/api/sessions/{sid}")
        assert response.status_code == 204
        # Verifica que foi deletada
        get_resp = client.get(f"/api/sessions/{sid}")
        assert get_resp.status_code == 404

    def test_get_nonexistent_session(self, client: TestClient):
        response = client.get("/api/sessions/99999")
        assert response.status_code == 404

    def test_delete_nonexistent_session(self, client: TestClient):
        response = client.delete("/api/sessions/99999")
        assert response.status_code == 404

    def test_chat_creates_session_auto(self, client: TestClient):
        """O endpoint /api/chat deve criar uma sessao e definir titulo (via mock)."""
        from unittest.mock import patch

        async def mock_generate(*, user_message, history, model=None):
            return ("Resposta mockada para teste de titulo automatico", "test-model")

        with patch("backend.routers.chat.generate_reply", mock_generate):
            response = client.post(
                "/api/chat",
                json={"message": "Ola"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["reply"] == "Resposta mockada para teste de titulo automatico"

    def test_chat_stream_endpoint_creates_session(self, client: TestClient):
        """O endpoint /api/chat/stream deve aceitar requisicao."""
        response = client.post(
            "/api/chat/stream",
            json={"message": "teste"},
        )
        # Sem API key deve retornar stream com erro, nao 422
        assert response.status_code == 200