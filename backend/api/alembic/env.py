# backend/api/alembic/env.py

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import make_url

# --- Make `src` importable (keep your path logic) ---
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

# Import metadata from your models
from src.models import Base  # noqa: E402

# Alembic Config object (reads alembic.ini)
config = context.config

# Configure logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate
target_metadata = Base.metadata


def _sync_url_from_env_or_ini() -> str:
    """
    Prefer TEST_DATABASE_URL, then DATABASE_URL, else alembic.ini sqlalchemy.url.
    Convert async driver names to sync equivalents for Alembic:
      - postgresql+asyncpg -> postgresql+psycopg
      - sqlite+aiosqlite  -> sqlite
    """
    raw = (
        os.getenv("TEST_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or config.get_main_option("sqlalchemy.url")
    )
    if not raw:
        raise RuntimeError("No DATABASE_URL / TEST_DATABASE_URL / sqlalchemy.url provided")

    url = make_url(raw)
    drv = url.drivername
    if "+asyncpg" in drv:
        url = url.set(drivername=drv.replace("+asyncpg", "+psycopg"))
    elif drv == "sqlite+aiosqlite":
        url = url.set(drivername="sqlite")
    return str(url)


# Ensure Alembic uses a SYNC URL even if the app runs async
config.set_main_option("sqlalchemy.url", _sync_url_from_env_or_ini())


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode'."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode' using a sync engine."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
