from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings
from app.core.database import Base, get_session
from app.main import app


@pytest_asyncio.fixture
async def client(tmp_path: Path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def session_override():
        async with sessions() as session:
            yield session

    test_settings = Settings(
        upload_dir=tmp_path / "uploads",
        export_dir=tmp_path / "exports",
        checkpoint_database_path=tmp_path / "checkpoints.sqlite",
    )
    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: test_settings
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()
    await engine.dispose()
