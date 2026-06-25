from __future__ import annotations

import bcrypt
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import AuthToken, User
from backend.schemas.auth import AuthResponse, LoginRequest, SignUpRequest


router = APIRouter()


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization:
        raise HTTPException(status_code=401, detail="Token nao fornecido")

    scheme, _, token_value = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token_value:
        raise HTTPException(status_code=401, detail="Formato de token invalido")

    token = (
        db.query(AuthToken)
        .filter(AuthToken.token == token_value, AuthToken.is_active == True)
        .first()
    )
    if not token:
        raise HTTPException(status_code=401, detail="Token invalido ou expirado")

    user = db.query(User).filter(User.id == token.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario nao encontrado")

    return user


@router.post("/api/auth/signup", response_model=AuthResponse)
def signup(payload: SignUpRequest, db: Session = Depends(get_db)) -> AuthResponse:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email ja cadastrado")

    hashed = _hash_password(payload.password)
    user = User(name=payload.name, email=payload.email, hashed_password=hashed)
    db.add(user)
    db.flush()

    token = AuthToken(user_id=user.id)
    db.add(token)
    db.commit()
    db.refresh(user)
    db.refresh(token)

    return AuthResponse(token=token.token, user_id=user.id, name=user.name, email=user.email)


@router.post("/api/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not _verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email ou senha invalidos")

    token = AuthToken(user_id=user.id)
    db.add(token)
    db.commit()
    db.refresh(token)

    return AuthResponse(token=token.token, user_id=user.id, name=user.name, email=user.email)


@router.post("/api/auth/logout")
def logout(
    current_user: User = Depends(get_current_user),
    authorization: str = Header(None),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    scheme, _, token_value = authorization.partition(" ")
    token = (
        db.query(AuthToken)
        .filter(AuthToken.token == token_value, AuthToken.is_active == True)
        .first()
    )
    if token:
        token.is_active = False
        db.commit()

    return {"message": "Logout realizado com sucesso"}


@router.get("/api/auth/me")
def get_me(current_user: User = Depends(get_current_user)) -> AuthResponse:
    return AuthResponse(
        token="",
        user_id=current_user.id,
        name=current_user.name,
        email=current_user.email,
    )