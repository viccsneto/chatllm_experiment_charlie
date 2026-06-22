from __future__ import annotations

from datetime import datetime, timezone

import bcrypt
import jwt
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session as DBSession

from backend.config import JWT_ALGORITHM, JWT_EXPIRATION_HOURS, JWT_SECRET
from backend.database import get_db
from backend.models import User
from backend.schemas.auth import AuthResponse, UserLogin, UserRegister

router = APIRouter()


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _create_token(user_id: int, email: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc).timestamp() + JWT_EXPIRATION_HOURS * 3600,
        "iat": datetime.now(timezone.utc).timestamp(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token. Raises HTTPException on failure."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token invalido.")


@router.post("/api/auth/register", response_model=AuthResponse, status_code=201)
def register(payload: UserRegister, db: DBSession = Depends(get_db)):
    email = payload.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Email invalido.")

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email ja cadastrado.")

    user = User(
        email=email,
        hashed_password=_hash_password(payload.password),
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = _create_token(user.id, user.email)
    return AuthResponse(token=token, email=user.email, user_id=user.id)


@router.post("/api/auth/login", response_model=AuthResponse)
def login(payload: UserLogin, db: DBSession = Depends(get_db)):
    email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Email ou senha incorretos.")

    if not _verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email ou senha incorretos.")

    token = _create_token(user.id, user.email)
    return AuthResponse(token=token, email=user.email, user_id=user.id)


@router.get("/api/auth/me")
def get_me(authorization: str = Header(None), db: DBSession = Depends(get_db)):
    """Return current user info if token is valid."""
    try:
        payload = decode_token(authorization.replace("Bearer ", "")) if authorization else None
    except Exception:
        raise HTTPException(status_code=401, detail="Token invalido.")
    if not payload:
        raise HTTPException(status_code=401, detail="Token ausente.")
    user = db.query(User).filter(User.id == payload.get("user_id")).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario nao encontrado.")
    return {"user_id": user.id, "email": user.email}


def get_current_user_id(authorization: str = Header(None)) -> int | None:
    """Extract user_id from Authorization header. Returns None if no/invalid token."""
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    try:
        payload = decode_token(parts[1])
        return payload.get("user_id")
    except HTTPException:
        return None