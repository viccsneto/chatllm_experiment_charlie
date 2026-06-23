from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from backend.config import ACCESS_TOKEN_EXPIRE_MINUTES
from backend.database import get_db
from backend.models import User
from backend.schemas.auth import UserCreate, UserLogin, UserOut
from backend.services.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

router = APIRouter()

COOKIE_KEY = "access_token"
COOKIE_PATH = "/"


def _set_token_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_KEY,
        value=token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        samesite="lax",
        path=COOKIE_PATH,
    )


def _clear_token_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_KEY, path=COOKIE_PATH)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    token = request.cookies.get(COOKIE_KEY)
    if not token:
        return None
    payload = decode_access_token(token)
    if payload is None:
        return None
    user_id = payload.get("sub")
    if user_id is None:
        return None
    user = db.query(User).filter(User.id == int(user_id)).first()
    return user


def require_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user = get_current_user(request, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Autenticacao necessaria")
    return user


@router.post("/api/auth/register", status_code=201)
def register(payload: UserCreate, response: Response, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email ja cadastrado")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user_id=user.id, email=user.email)
    _set_token_cookie(response, token)

    return UserOut(id=user.id, email=user.email)


@router.post("/api/auth/login")
def login(payload: UserLogin, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email ou senha invalidos")

    token = create_access_token(user_id=user.id, email=user.email)
    _set_token_cookie(response, token)

    return UserOut(id=user.id, email=user.email)


@router.post("/api/auth/logout")
def logout(response: Response):
    _clear_token_cookie(response)
    return {"message": "Logout realizado"}


@router.get("/api/auth/me")
def me(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Nao autenticado")
    return UserOut(id=user.id, email=user.email)