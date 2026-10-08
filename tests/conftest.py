import os
from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy import text

from cache_service.config import Settings
from cache_service.database import create_engine, create_tables
from cache_service.main import create_app
from tests.fakes import CountingTransformer

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://cache:cache@localhost:5433/cache"
)


@pytest.fixture
def transformer() -> CountingTransformer:
    return CountingTransformer()


@pytest.fixture
async def client(transformer: CountingTransformer) -> AsyncIterator[httpx.AsyncClient]:
    engine = create_engine(TEST_DATABASE_URL)
    await create_tables(engine)
    async with engine.begin() as connection:
        await connection.execute(text("TRUNCATE payloads, transformations"))
    await engine.dispose()

    app = create_app(Settings(database_url=TEST_DATABASE_URL), transformer)
    transport = httpx.ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://test") as client,
    ):
        yield client
