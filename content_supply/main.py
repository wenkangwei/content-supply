"""FastAPI application factory with lifespan management."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from content_supply.config import load_app_config
from content_supply.db import close_db, create_tables, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB + Redis. Shutdown: cleanup."""
    config = load_app_config()
    init_db(config)
    await create_tables()
    yield
    await close_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Content Supply Platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Register routers
    from content_supply.api.health import router as health_router
    app.include_router(health_router, prefix="/api", tags=["health"])

    return app


app = create_app()
