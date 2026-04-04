"""Async SQLAlchemy engine and session management."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from content_supply.config import AppConfig

_engine = None
_session_factory = None


def init_db(config: AppConfig) -> None:
    global _engine, _session_factory
    _engine = create_async_engine(
        config.mysql.dsn,
        pool_size=config.mysql.pool_size,
        echo=False,
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
