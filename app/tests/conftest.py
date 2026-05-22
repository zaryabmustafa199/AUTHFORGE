"""
Test Configuration — Fixtures for AuthForge test suite.

Creates all tables from ORM models (bypasses Alembic for tests),
truncates data between tests for isolation, and creates engine/Redis
lazily inside the test event loop.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

from app.config import settings
from app.models import Base


@pytest_asyncio.fixture
async def test_engine():
    """Creates a test engine and ensures tables exist."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    # Create all tables from ORM models
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session_maker(test_engine):
    """Creates a session factory from the test engine."""
    return async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def test_redis():
    """Creates a test Redis client."""
    import redis.asyncio as aioredis
    client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    yield client
    await client.aclose()


@pytest_asyncio.fixture(autouse=True)
async def clean_data(test_engine, test_session_maker, test_redis):
    """Truncate all data and re-seed roles before each test."""
    async with test_engine.begin() as conn:
        # Truncate in FK-safe order
        await conn.execute(text(
            "TRUNCATE TABLE audit_logs, sessions, users, roles RESTART IDENTITY CASCADE"
        ))

    # Re-seed roles
    async with test_session_maker() as session:
        from app.models.role import Role
        session.add_all([
            Role(name="user", permissions=["read_own", "write_own"]),
            Role(name="moderator", permissions=["read_all", "ban_users"]),
            Role(name="admin", permissions=["read_all", "write_all", "manage_users", "manage_roles"]),
        ])
        await session.commit()

    await test_redis.flushdb()
    yield
    await test_redis.flushdb()


@pytest_asyncio.fixture
async def client(test_session_maker, test_redis):
    """Async HTTP test client with dependency overrides."""
    from app.main import app
    from app.api.deps import get_db
    from app.redis import get_redis

    _maker = test_session_maker
    _redis = test_redis

    async def _test_db():
        async with _maker() as session:
            yield session

    async def _test_redis():
        return _redis

    app.dependency_overrides[get_db] = _test_db
    app.dependency_overrides[get_redis] = _test_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def db_session(test_session_maker):
    """Direct database session for test assertions."""
    async with test_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient):
    """Creates a test user and returns (headers, tokens)."""
    await client.post("/api/v1/auth/signup", json={
        "email": "testuser@test.com",
        "password": "TestPass123!",
    })
    login_resp = await client.post("/api/v1/auth/login", data={
        "username": "testuser@test.com",
        "password": "TestPass123!",
    })
    tokens = login_resp.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    return headers, tokens


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient, db_session):
    """Creates an admin user and returns (headers, tokens)."""
    await client.post("/api/v1/auth/signup", json={
        "email": "admin@test.com",
        "password": "AdminPass123!",
    })

    from sqlalchemy.future import select
    from app.models.user import User
    result = await db_session.execute(select(User).where(User.email == "admin@test.com"))
    admin_user = result.scalars().first()
    admin_user.role_id = 3
    admin_user.is_verified = True
    await db_session.commit()

    login_resp = await client.post("/api/v1/auth/login", data={
        "username": "admin@test.com",
        "password": "AdminPass123!",
    })
    tokens = login_resp.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    return headers, tokens
