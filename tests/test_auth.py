from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from backend.models import User as UserModel


class TestAuthAPI:
    def test_register_success(self, client: TestClient):
        response = client.post(
            "/api/auth/register",
            json={"email": "teste@email.com", "password": "123456"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["email"] == "teste@email.com"
        assert data["token_type"] == "bearer"

    def test_register_duplicate_email(self, client: TestClient):
        client.post("/api/auth/register", json={"email": "dup@email.com", "password": "123456"})
        response = client.post("/api/auth/register", json={"email": "dup@email.com", "password": "654321"})
        assert response.status_code == 409
        assert "ja cadastrado" in response.json()["detail"]

    def test_register_with_display_name(self, client: TestClient):
        response = client.post(
            "/api/auth/register",
            json={"email": "nome@email.com", "password": "123456", "display_name": "Joao"},
        )
        assert response.status_code == 201
        assert response.json()["display_name"] == "Joao"

    def test_login_success(self, client: TestClient):
        client.post("/api/auth/register", json={"email": "login@email.com", "password": "123456"})
        response = client.post("/api/auth/login", json={"email": "login@email.com", "password": "123456"})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["email"] == "login@email.com"

    def test_login_wrong_password(self, client: TestClient):
        client.post("/api/auth/register", json={"email": "wrong@email.com", "password": "correct"})
        response = client.post("/api/auth/login", json={"email": "wrong@email.com", "password": "wrong"})
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client: TestClient):
        response = client.post("/api/auth/login", json={"email": "noone@email.com", "password": "123456"})
        assert response.status_code == 401

    def test_me_authenticated(self, client: TestClient):
        client.post("/api/auth/register", json={"email": "me@email.com", "password": "123456"})
        login_resp = client.post("/api/auth/login", json={"email": "me@email.com", "password": "123456"})
        token = login_resp.json()["access_token"]

        response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "me@email.com"

    def test_me_unauthenticated(self, client: TestClient):
        response = client.get("/api/auth/me")
        assert response.status_code == 200
        assert response.json() is None

    def test_me_invalid_token(self, client: TestClient):
        response = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid-token"})
        assert response.status_code == 200
        assert response.json() is None

    def test_logout(self, client: TestClient):
        response = client.post("/api/auth/logout")
        assert response.status_code == 200
        assert response.json()["message"] == "Logout realizado com sucesso"

    def test_register_short_password(self, client: TestClient):
        response = client.post("/api/auth/register", json={"email": "short@email.com", "password": "12345"})
        assert response.status_code == 422