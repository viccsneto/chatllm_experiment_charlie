from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.config import SQLALCHEMY_DATABASE_URL, SQLITE_PATH


Path(SQLITE_PATH).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def run_migrations():
    """Executa migracoes automaticas para manter o schema atualizado.

    SQLite + SQLAlchemy create_all nao altera tabelas existentes,
    entao precisamos adicionar colunas faltantes manualmente.
    """
    from sqlalchemy import text

    inspector = inspect(engine)
    existing_columns = {col["name"] for col in inspector.get_columns("sessions")} if inspector.has_table("sessions") else set()

    if inspector.has_table("sessions") and "user_id" not in existing_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE sessions ADD COLUMN user_id INTEGER REFERENCES users(id)"))
            conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
