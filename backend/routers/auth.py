from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import ApiToken, User
from backend.schemas.auth import (
    AuthResponse,
    LoginRequest,
    LogoutResponse,
    MeResponse,
    SignupRequest,
)
from backend.services.auth import (
    create_jwt,
    decode_jwt,
    generate_token,
    hash_email,
    hash_password,
    verify_email,
    verify_password,
)


router = APIRouter()


def _get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """Dependency: extract and validate Bearer token, return user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token nao fornecido")
    jwt_part = authorization.removeprefix("Bearer ").strip()

    # First try JWT validation
    payload = decode_jwt(jwt_part)
    if payload:
        email_hash = payload.get("sub") or ""
        user = db.query(User).filter(User.email_hash == email_hash).first()
        if user:
            return user

    # Fallback: opaque token lookup
    token_hash = _hash_token(jwt_part)
    api_token = (
        db.query(ApiToken)
        .filter(
            ApiToken.token_hash == token_hash,
            ApiToken.active == True,
        )
        .first()
    )
    if not api_token:
        raise HTTPException(status_code=401, detail="Token invalido ou expirado")

    if api_token.expires_at and api_token.expires_at.replace(tzinfo=None) < datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(status_code=401, detail="Token expirado")

    user = db.query(User).filter(User.id == api_token.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario nao encontrado")
    return user


def _hash_token(token: str) -> str:
    """Hash a bearer token for storage."""
    import hashlib
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/api/auth/signup", response_model=AuthResponse, status_code=201)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    email_hash = hash_email(payload.email)
    existing = db.query(User).filter(User.email_hash == email_hash).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email ja cadastrado")

    user = User(
        email_hash=email_hash,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate both JWT and opaque token
    jwt_token = create_jwt(payload.email)
    return AuthResponse(token=jwt_token, email=payload.email)


@router.post("/api/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email_hash == hash_email(payload.email)).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email ou senha invalidos")

    jwt_token = create_jwt(payload.email)
    return AuthResponse(token=jwt_token, email=payload.email)


@router.post("/api/auth/logout", response_model=LogoutResponse)
def logout(
    current_user: User = Depends(_get_current_user),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    # Invalidate the token by marking it inactive if it's an opaque token
    token_str = (authorization or "").removeprefix("Bearer ").strip()
    token_hash = _hash_token(token_str)
    api_token = db.query(ApiToken).filter(ApiToken.token_hash == token_hash).first()
    if api_token:
        api_token.active = False
        db.commit()
    # For JWTs, we rely on expiration — no server-side invalidation needed.
    return LogoutResponse()


@router.get("/api/auth/me", response_model=MeResponse)
def me(current_user: User = Depends(_get_current_user)):
    return MeResponse(email="Usuario autenticado")