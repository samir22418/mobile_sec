from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import Base
import app.models  # noqa: F401 — register all ORM classes with Base.metadata

target_metadata = Base.metadata

_PLACEHOLDER = "driver://user:pass@localhost/dbname"


def _get_url() -> str:
    """
    Prefer the URL set programmatically via cfg.set_main_option()
    (used by init_db() for Postgres). Fall back to load_settings() for the CLI.
    """
    url = config.get_main_option("sqlalchemy.url", "")
    if not url or url == _PLACEHOLDER:
        from app.config import load_settings
        url = load_settings().database_url
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=_get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        {"sqlalchemy.url": _get_url()},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
