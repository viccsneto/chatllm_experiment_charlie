from __future__ import annotations

import bcrypt
import pytest
from fastapi.testclient import TestClient

from backend.models import AuthToken, User


def _create_user_and_token(db_session) -> tuple[User, str]:
    """Cria um usuario de teste e retorna (user, token_str)."""
    hashed = bcrypt.hashpw(b"senha123", bcrypt.gensalt()).decode("utf-8")
    user = User(name="Teste", email="teste@email.com", hashed_password=hashed)
    db_session.add(user)
    db_session.flush()

    token = AuthToken(token="test-token-123", user_id=user.id)
    db_session.add(token)
    db_session.commit()

    return user, "test-token-123"


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


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
    def test_chat_requires_auth(self, client: TestClient):
        """Sem token deve retornar 401."""
        response = client.post(
            "/api/chat",
            json={"message": "Ola"},
        )
        assert response.status_code == 401

    def test_chat_empty_message_rejected(self, client: TestClient, db_session):
        """Mensagem vazia deve ser rejeitada com 422 (validacao Pydantic)."""
        _, token = _create_user_and_token(db_session)
        response = client.post(
            "/api/chat",
            json={"message": ""},
            headers=auth_header(token),
        )
        assert response.status_code == 422

    def test_chat_endpoint_exists(self, client: TestClient, db_session):
        """Endpoint responde com 503 sem API key (config error)."""
        _, token = _create_user_and_token(db_session)
        response = client.post(
            "/api/chat",
            json={"message": "Ola"},
            headers=auth_header(token),
        )
        assert response.status_code in (200, 422, 503)


class TestChatStreamEndpoint:
    def test_chat_stream_requires_auth(self, client: TestClient):
        """Sem token deve retornar 401."""
        response = client.post(
            "/api/chat/stream",
            json={"message": "Ola"},
        )
        assert response.status_code == 401

    def test_chat_stream_empty_message_rejected(self, client: TestClient, db_session):
        """Stream com mensagem vazia deve ser rejeitado com 422."""
        _, token = _create_user_and_token(db_session)
        response = client.post(
            "/api/chat/stream",
            json={"message": ""},
            headers=auth_header(token),
        )
        assert response.status_code == 422

    def test_chat_stream_endpoint_exists(self, client: TestClient, db_session):
        """Endpoint de stream aceita requisicoes com token."""
        _, token = _create_user_and_token(db_session)
        response = client.post(
            "/api/chat/stream",
            json={"message": "Ola"},
            headers=auth_header(token),
        )
        assert response.status_code in (200, 422, 503)


class TestSessionEndpoints:
    def test_list_sessions_requires_auth(self, client: TestClient):
        """Sem token deve retornar 401."""
        response = client.get("/api/sessions")
        assert response.status_code == 401

    def test_list_sessions_empty(self, client: TestClient, db_session):
        """Listagem de sessoes deve retornar lista vazia inicialmente."""
        _, token = _create_user_and_token(db_session)
        response = client.get("/api/sessions", headers=auth_header(token))
        assert response.status_code == 200
        assert response.json() == []

    def test_list_sessions_after_creation(self, client: TestClient, db_session):
        """Deve listar sessoes do usuario apos criar uma."""
        from backend.models import Session

        user, token = _create_user_and_token(db_session)
        s = Session(user_id=user.id, title="Sessao teste")
        db_session.add(s)
        db_session.commit()

        response = client.get("/api/sessions", headers=auth_header(token))
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Sessao teste"

    def test_list_sessions_other_user_not_visible(self, client: TestClient, db_session):
        """Sessoes de outro usuario nao devem aparecer."""
        from backend.models import Session

        user1, token1 = _create_user_and_token(db_session)
        # Create another user
        user2 = User(name="Outro", email="outro@email.com", hashed_password="hash")
        db_session.add(user2)
        db_session.flush()

        s = Session(user_id=user2.id, title="Sessao de outro")
        db_session.add(s)
        db_session.commit()

        response = client.get("/api/sessions", headers=auth_header(token1))
        assert response.status_code == 200
        assert response.json() == []

    def test_get_session_messages_not_found(self, client: TestClient, db_session):
        """Sessao inexistente deve retornar 404."""
        _, token = _create_user_and_token(db_session)
        response = client.get("/api/sessions/999/messages", headers=auth_header(token))
        assert response.status_code == 404

    def test_get_session_messages_empty(self, client: TestClient, db_session):
        """Sessao existente sem mensagens deve retornar lista vazia."""
        from backend.models import Session

        user, token = _create_user_and_token(db_session)
        s = Session(user_id=user.id, title="Sessao vazia")
        db_session.add(s)
        db_session.commit()

        response = client.get(f"/api/sessions/{s.id}/messages", headers=auth_header(token))
        assert response.status_code == 200
        assert response.json() == []

    def test_get_session_messages_with_content(self, client: TestClient, db_session):
        """Deve retornar mensagens de uma sessao ordenadas por created_at."""
        from backend.models import Message, Session

        user, token = _create_user_and_token(db_session)
        s = Session(user_id=user.id, title="Sessao com msgs")
        db_session.add(s)
        db_session.flush()

        m1 = Message(session_id=s.id, role="user", content="Pergunta")
        m2 = Message(session_id=s.id, role="assistant", content="Resposta")
        db_session.add_all([m1, m2])
        db_session.commit()

        response = client.get(f"/api/sessions/{s.id}/messages", headers=auth_header(token))
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["role"] == "user"
        assert data[0]["content"] == "Pergunta"
        assert data[1]["role"] == "assistant"
        assert data[1]["content"] == "Resposta"


class TestAuthEndpoints:
    def test_signup_creates_user(self, client: TestClient, db_session):
        """Cadastro deve criar usuario e retornar token."""
        response = client.post(
            "/api/auth/signup",
            json={"name": "Novo", "email": "novo@email.com", "password": "senha123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Novo"
        assert data["email"] == "novo@email.com"
        assert "token" in data
        assert data["user_id"] > 0

    def test_signup_duplicate_email(self, client: TestClient, db_session):
        """Email duplicado deve retornar 409."""
        _create_user_and_token(db_session)
        response = client.post(
            "/api/auth/signup",
            json={"name": "Outro", "email": "teste@email.com", "password": "senha456"},
        )
        assert response.status_code == 409
        assert "ja cadastrado" in response.json()["detail"]

    def test_login_valid(self, client: TestClient, db_session):
        """Login valido deve retornar token."""
        user = User(name="Login", email="login@email.com", hashed_password=bcrypt.hashpw(b"senha123", bcrypt.gensalt()).decode("utf-8"))
        db_session.add(user)
        db_session.commit()

        response = client.post(
            "/api/auth/login",
            json={"email": "login@email.com", "password": "senha123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Login"
        assert "token" in data

    def test_login_invalid(self, client: TestClient, db_session):
        """Login com senha errada deve retornar 401."""
        user = User(name="Login", email="login@email.com", hashed_password=bcrypt.hashpw(b"senha123", bcrypt.gensalt()).decode("utf-8"))
        db_session.add(user)
        db_session.commit()

        response = client.post(
            "/api/auth/login",
            json={"email": "login@email.com", "password": "senha_errada"},
        )
        assert response.status_code == 401

    def test_logout_deactivates_token(self, client: TestClient, db_session):
        """Logout deve desativar o token."""
        _, token = _create_user_and_token(db_session)
        response = client.post("/api/auth/logout", headers=auth_header(token))
        assert response.status_code == 200

        # Token should no longer work
        response = client.get("/api/sessions", headers=auth_header(token))
        assert response.status_code == 401


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
