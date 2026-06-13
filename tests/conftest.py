import pytest_asyncio, pytest
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from main import app
from dbLogic import get_session
from models import settings
from sqlalchemy.pool import NullPool


engine = create_async_engine(
    settings.TEST_DATABASE_URL, 
    echo=False, 
    future=True, 
    poolclass=NullPool
)
TestSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)



@pytest.fixture(scope="session")
def event_loop():
    ''' Event loop for async tests '''
    import asyncio
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def init_database():
    ''' Create(on startup) and Drop(on shutdown) the testing database '''
    
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clear_redis():
    ''' Close redis connection '''
    yield
    from dbLogic import redis_client
    if hasattr(redis_client, "connection_pool"):
        await redis_client.connection_pool.disconnect()



@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    ''' To use the database for our tests '''
    
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()



@pytest.fixture(autouse=True)
def override_get_session(db_session):
    ''' Overrides the session '''
    
    async def _get_test_session():
        yield db_session
    app.dependency_overrides[get_session] = _get_test_session
    yield
    app.dependency_overrides.clear()



@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    ''' Async client '''
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
