from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone, timedelta

import jwt
from passlib.context import CryptContext

from backend.config import SECRET_KEY, TOKEN_EXPIRE_HOURS


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def hash_email(email: str) -> str:
    """Hash email with SHA-256 for storage (privacy: never store raw email)."""
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()


def verify_email(raw: str, stored_hash: str) -> bool:
    return hash_email(raw) == stored_hash


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(raw: str, hashed: str) -> bool:
    return pwd_context.verify(raw, hashed)


def generate_token() -> str:
    return secrets.token_urlsafe(48)


def create_jwt(email: str) -> str:
    """Create a short-lived JWT containing the email hash as identifier."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": hash_email(email),
        "iat": now,
        "exp": now + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_jwt(token: str) -> dict | None:
    """Decode and validate a JWT. Returns payload dict or None."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None