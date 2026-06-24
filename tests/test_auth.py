from __future__ import annotations

from fastapi.testclient import TestClient


class TestSignup:
    def test_signup_success(self, client: TestClient):
        response = client.post(
            "/api/auth/signup",
            json={"email": "teste@example.com", "password": "123456"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "token" in data
        assert data["email"] == "teste@example.com"

    def test_signup_duplicate_email(self, client: TestClient):
        client.post("/api/auth/signup", json={"email": "dup@example.com", "password": "123456"})
        response = client.post(
            "/api/auth/signup",
            json={"email": "dup@example.com", "password": "654321"},
        )
        assert response.status_code == 409

    def test_signup_invalid_email(self, client: TestClient):
        response = client.post(
            "/api/auth/signup",
            json={"email": "invalido", "password": "123456"},
        )
        assert response.status_code == 422

    def test_signup_short_password(self, client: TestClient):
        response = client.post(
            "/api/auth/signup",
            json={"email": "a@b.com", "password": "123"},
        )
        assert response.status_code == 422


class TestLogin:
    def test_login_success(self, client: TestClient):
        client.post("/api/auth/signup", json={"email": "login@example.com", "password": "123456"})
        response = client.post(
            "/api/auth/login",
            json={"email": "login@example.com", "password": "123456"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data

    def test_login_wrong_password(self, client: TestClient):
        client.post("/api/auth/signup", json={"email": "wrong@example.com", "password": "123456"})
        response = client.post(
            "/api/auth/login",
            json={"email": "wrong@example.com", "password": "senha_errada"},
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client: TestClient):
        response = client.post(
            "/api/auth/login",
            json={"email": "naoexiste@example.com", "password": "123456"},
        )
        assert response.status_code == 401


class TestMe:
    def test_me_authenticated(self, client: TestClient):
        client.post("/api/auth/signup", json={"email": "me@example.com", "password": "123456"})
        login_resp = client.post(
            "/api/auth/login", json={"email": "me@example.com", "password": "123456"}
        )
        token = login_resp.json()["token"]

        response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200

    def test_me_no_token(self, client: TestClient):
        response = client.get("/api/auth/me")
        assert response.status_code in (401, 422)  # 422 when Header param is missing

    def test_me_invalid_token(self, client: TestClient):
        response = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid_token_123"})
        assert response.status_code == 401


class TestLogout:
    def test_logout_success(self, client: TestClient):
        client.post("/api/auth/signup", json={"email": "logout@example.com", "password": "123456"})
        login_resp = client.post(
            "/api/auth/login", json={"email": "logout@example.com", "password": "123456"}
        )
        token = login_resp.json()["token"]

        response = client.post(
            "/api/auth/logout", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Desconectado com sucesso"

    def test_logout_no_token(self, client: TestClient):
        response = client.post("/api/auth/logout")
        assert response.status_code in (401, 422)  # 422 when Header param is missing