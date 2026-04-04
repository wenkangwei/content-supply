"""FastAPI application factory with lifespan management."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from content_supply.config import load_app_config
from content_supply.db import close_db, create_tables, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB. Shutdown: cleanup."""
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

    from content_supply.api.health import router as health_router
    from content_supply.api.feeds import router as feeds_router
    from content_supply.api.items import router as items_router
    from content_supply.api.crawl import router as crawl_router
    from content_supply.api.hot import router as hot_router
    from content_supply.api.rewrite import router as rewrite_router
    from content_supply.api.cleanup import router as cleanup_router
    from content_supply.api.tags import router as tags_router

    app.include_router(health_router, prefix="/api", tags=["health"])
    app.include_router(feeds_router, prefix="/api", tags=["feeds"])
    app.include_router(items_router, prefix="/api", tags=["items"])
    app.include_router(crawl_router, prefix="/api", tags=["crawl"])
    app.include_router(hot_router, prefix="/api", tags=["hot"])
    app.include_router(rewrite_router, prefix="/api", tags=["rewrite"])
    app.include_router(cleanup_router, prefix="/api", tags=["cleanup"])
    app.include_router(tags_router, prefix="/api", tags=["tags"])

    return app


app = create_app()
