from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

_BACKEND_DIR = Path(__file__).resolve().parent.parent


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str):
    if database_url.startswith("sqlite"):
        url = make_url(database_url)
        if url.database and url.database != ":memory:":
            Path(url.database).parent.mkdir(parents=True, exist_ok=True)
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args, future=True)


def make_session_factory(database_url: str) -> sessionmaker[Session]:
    return sessionmaker(bind=make_engine(database_url), autoflush=False, autocommit=False, expire_on_commit=False)


def init_db(session_factory: sessionmaker[Session]) -> None:
    engine = session_factory.kw["bind"]
    if str(engine.url).startswith("postgresql"):
        _run_alembic_to_head(engine)
    else:
        Base.metadata.create_all(engine)
        ensure_runtime_schema(engine)


def _run_alembic_to_head(engine) -> None:
    """Run all pending Alembic migrations against the given engine."""
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(_BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", str(engine.url))
    command.upgrade(cfg, "head")


def ensure_runtime_schema(engine) -> None:
    """SQLite-only shim for DBs created before the provider column was added."""
    if not str(engine.url).startswith("sqlite"):
        return
    inspector = inspect(engine)
    if "ai_model_runs" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("ai_model_runs")}
    if "provider" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE ai_model_runs ADD COLUMN provider VARCHAR(64) DEFAULT 'unknown'"))


def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
