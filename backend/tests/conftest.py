import os
import sys
import uuid
from typing import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import close_pool, get_pool
from app.core.security import hash_password
from app.main import app
from app.services.auth_service import create_access_token_for_user, get_user_by_email


@pytest.fixture(autouse=True)
async def _reset_pool() -> AsyncGenerator[None, None]:
    yield
    try:
        await close_pool()
    except Exception:
        pass


@pytest.fixture
async def pool():
    return await get_pool()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
async def admin_token() -> str:
    user = await get_user_by_email("admin@le-seizieme.local")
    assert user is not None, "Admin user not found in database"
    return create_access_token_for_user(user)


@pytest.fixture
async def manager_token() -> str:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users (email, hashed_password, role, is_active)
            VALUES ($1, $2, 'MANAGER', TRUE)
            ON CONFLICT (email) DO NOTHING
            """,
            "manager@test.com",
            hash_password("TestPassword123!"),
        )
    user = await get_user_by_email("manager@test.com")
    assert user is not None
    return create_access_token_for_user(user)


@pytest.fixture
async def staff_token() -> str:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users (email, hashed_password, role, is_active)
            VALUES ($1, $2, 'STAFF', TRUE)
            ON CONFLICT (email) DO NOTHING
            """,
            "staff@test.com",
            hash_password("TestPassword123!"),
        )
    user = await get_user_by_email("staff@test.com")
    assert user is not None
    return create_access_token_for_user(user)


@pytest.fixture
def test_event_id() -> uuid.UUID:
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def test_server_id() -> uuid.UUID:
    return uuid.UUID("00000000-0000-0000-0000-000000000002")
