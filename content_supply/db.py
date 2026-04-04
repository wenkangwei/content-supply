"""Async SQLAlchemy engine and session management."""

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from content_supply.config import AppConfig

_engine = None
_session_factory = None


def _get_db_url(config: AppConfig) -> str:
    """Determine DB URL — use SQLite for local dev if MySQL is unavailable."""
    # Check env override first
    env_url = os.environ.get("DATABASE_URL")
    if env_url:
        return env_url

    # Try MySQL if explicitly requested
    if os.environ.get("DB_ENGINE", "").lower() == "mysql":
        return config.mysql.dsn

    # Default: SQLite for easy local development
    db_path = os.environ.get("SQLITE_PATH", "content_supply.db")
    return f"sqlite+aiosqlite:///{db_path}"


def init_db(config: AppConfig) -> None:
    global _engine, _session_factory
    db_url = _get_db_url(config)

    connect_args = {}
    if "sqlite" in db_url:
        connect_args["check_same_thread"] = False

    _engine = create_async_engine(
        db_url,
        pool_size=config.mysql.pool_size if "mysql" in db_url else 5,
        echo=False,
        connect_args=connect_args,
    )
    _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def create_tables() -> None:
    """Create all tables (for development; use Alembic in production)."""
    from content_supply.models.base import Base
    if _engine is None:
        raise RuntimeError("Database not initialized.")
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
