import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from cache_service.api import router
from cache_service.config import Settings
from cache_service.database import create_engine, create_session_factory, create_tables
from cache_service.transformer import SimulatedTransformer, Transformer


def create_app(settings: Settings | None = None, transformer: Transformer | None = None) -> FastAPI:
    """Build the app; tests pass their own settings and a fake transformer."""
    app_settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
        engine = create_engine(app_settings.database_url)
        await create_tables(engine)
        app.state.session_factory = create_session_factory(engine)
        app.state.transformer = transformer or SimulatedTransformer(
            app_settings.transformer_delay_seconds
        )
        yield
        await engine.dispose()

    app = FastAPI(title="Payload cache", lifespan=lifespan)
    app.include_router(router)
    return app
