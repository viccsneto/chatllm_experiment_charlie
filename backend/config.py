from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL_DEFAULT = os.getenv("OPENROUTER_MODEL", "google/gemma-4-31b-it")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

SQLITE_PATH = ROOT_DIR / "database" / "chat.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{SQLITE_PATH}"

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY nao definida no .env. Gere uma com: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
    )

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
