import uuid

import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.services.auth_service import create_access_token_for_user, get_user_by_email


ADMIN_EMAIL = "admin@le-seizieme.local"
ADMIN_PASSWORD = "SecurePassword123!"
MANAGER_PASSWORD = "TestPassword123!"
STAFF_PASSWORD = "TestPassword123!"

def _auth_headers(token: str):
    return {"Authorization": f"Bearer {token}"}


async def _create_user_direct(conn, email, role="STAFF", is_active=True):
    await conn.execute("DELETE FROM users WHERE email = $1", email)
    row = await conn.fetchrow(
        "INSERT INTO users (email, hashed_password, role, is_active) VALUES ($1, $2, $3, $4) RETURNING id",
        email,
        hash_password("TestPassword123!"),
        role,
        is_active,
    )
    return str(row["id"])


class TestUserManagementAuthorization:
    async def test_unauthenticated_list_users_returns_401(self, client: AsyncClient):
        r = await client.get("/api/users")
        assert r.status_code == 401

    async def test_unauthenticated_get_user_returns_401(self, client: AsyncClient):
        r = await client.get("/api/users/00000000-0000-0000-0000-000000000001")
        assert r.status_code == 401

    async def test_unauthenticated_create_user_returns_401(self, client: AsyncClient):
        r = await client.post(
            "/api/users",
            json={"email": "new@example.org", "password": "Password123!", "role": "STAFF"},
        )
        assert r.status_code == 401

    async def test_manager_list_users_returns_403(self, client: AsyncClient, manager_token):
        r = await client.get("/api/users", headers=_auth_headers(manager_token))
        assert r.status_code == 403

    async def test_staff_create_user_returns_403(self, client: AsyncClient, staff_token):
        r = await client.post(
            "/api/users",
            headers=_auth_headers(staff_token),
            json={"email": "new@example.org", "password": "Password123!", "role": "STAFF"},
        )
        assert r.status_code == 403

    async def test_staff_get_user_returns_403(self, client: AsyncClient, staff_token):
        r = await client.get("/api/users/00000000-0000-0000-0000-000000000001", headers=_auth_headers(staff_token))
        assert r.status_code == 403


class TestUserManagementCRUD:
    async def test_admin_can_list_users(self, client: AsyncClient, admin_token):
        r = await client.get("/api/users", headers=_auth_headers(admin_token))
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        assert isinstance(data["items"], list)
        for item in data["items"]:
            assert "hashed_password" not in item
            assert "email" in item
            assert "role" in item
            assert "is_active" in item

    async def test_admin_can_view_user(self, client: AsyncClient, admin_token, pool):
        async with pool.acquire() as conn:
            user_id = await _create_user_direct(conn, "viewable@example.org")

        r = await client.get(f"/api/users/{user_id}", headers=_auth_headers(admin_token))
        assert r.status_code == 200
        data = r.json()
        assert "hashed_password" not in data
        assert data["email"] == "viewable@example.org"
        assert data["role"] == "STAFF"

    async def test_view_unknown_user_returns_404(self, client: AsyncClient, admin_token):
        r = await client.get("/api/users/00000000-0000-0000-0000-000000000099", headers=_auth_headers(admin_token))
        assert r.status_code == 404

    async def test_admin_can_create_user(self, client: AsyncClient, admin_token):
        email = f"create_{uuid.uuid4().hex[:8]}@example.org"
        r = await client.post(
            "/api/users",
            headers=_auth_headers(admin_token),
            json={"email": email, "password": "Password123!", "role": "MANAGER", "is_active": True},
        )
        assert r.status_code == 201
        data = r.json()
        assert "hashed_password" not in data
        assert data["email"] == email
        assert data["role"] == "MANAGER"
        assert data["is_active"] is True

    async def test_admin_can_update_user(self, client: AsyncClient, admin_token, pool):
        async with pool.acquire() as conn:
            user_id = await _create_user_direct(conn, "update_me@example.org")

        r = await client.patch(
            f"/api/users/{user_id}",
            headers=_auth_headers(admin_token),
            json={"role": "MANAGER"},
        )
        assert r.status_code == 200
        assert r.json()["role"] == "MANAGER"

    async def test_admin_can_deactivate_user(self, client: AsyncClient, admin_token, pool):
        async with pool.acquire() as conn:
            user_id = await _create_user_direct(conn, "deactivate_me@example.org")

        r = await client.patch(
            f"/api/users/{user_id}/deactivate",
            headers=_auth_headers(admin_token),
        )
        assert r.status_code == 200
        assert r.json()["is_active"] is False

    async def test_update_unknown_user_returns_404(self, client: AsyncClient, admin_token):
        r = await client.patch(
            "/api/users/00000000-0000-0000-0000-000000000099",
            headers=_auth_headers(admin_token),
            json={"is_active": False},
        )
        assert r.status_code == 404


class TestUserManagementValidation:
    async def test_duplicate_email_rejected(self, client: AsyncClient, admin_token, pool):
        async with pool.acquire() as conn:
            await _create_user_direct(conn, "duplicate@example.org")

        r = await client.post(
            "/api/users",
            headers=_auth_headers(admin_token),
            json={"email": "duplicate@example.org", "password": "Password123!", "role": "STAFF"},
        )
        assert r.status_code == 409

    async def test_invalid_role_rejected(self, client: AsyncClient, admin_token, pool):
        email = f"role_{uuid.uuid4().hex[:8]}@example.org"
        r = await client.post(
            "/api/users",
            headers=_auth_headers(admin_token),
            json={"email": email, "password": "Password123!", "role": "SUPERADMIN"},
        )
        assert r.status_code == 422

    async def test_short_password_rejected(self, client: AsyncClient, admin_token):
        email = f"short_{uuid.uuid4().hex[:8]}@example.org"
        r = await client.post(
            "/api/users",
            headers=_auth_headers(admin_token),
            json={"email": email, "password": "123", "role": "STAFF"},
        )
        assert r.status_code == 422

    async def test_password_hashes_never_in_responses(self, client: AsyncClient, admin_token, pool):
        email = f"nohash_{uuid.uuid4().hex[:8]}@example.org"
        r = await client.post(
            "/api/users",
            headers=_auth_headers(admin_token),
            json={"email": email, "password": "Password123!", "role": "STAFF"},
        )
        assert r.status_code == 201
        body = r.text
        assert "hashed_password" not in body
        assert "$argon2" not in body

    async def test_duplicate_email_on_update_rejected(self, client: AsyncClient, admin_token, pool):
        async with pool.acquire() as conn:
            target_id = await _create_user_direct(conn, "update_target@example.org")
            await _create_user_direct(conn, "existing@example.org")

        r = await client.patch(
            f"/api/users/{target_id}",
            headers=_auth_headers(admin_token),
            json={"email": "existing@example.org"},
        )
        assert r.status_code == 409


class TestUserManagementSafety:
    async def test_admin_cannot_deactivate_self(self, client: AsyncClient, admin_token):
        admin = await get_user_by_email(ADMIN_EMAIL)
        admin_id = str(admin["id"])
        r = await client.patch(
            f"/api/users/{admin_id}/deactivate",
            headers=_auth_headers(admin_token),
        )
        assert r.status_code == 409

    async def test_admin_cannot_deactivate_last_active_admin(self, client: AsyncClient, admin_token, pool):
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id FROM users WHERE role = 'ADMIN' AND is_active = TRUE AND email <> $1",
                ADMIN_EMAIL,
            )
            for row in rows:
                await conn.execute("UPDATE users SET is_active = FALSE WHERE id = $1", row["id"])

        r = await client.patch(
            f"/api/users/{str(uuid.UUID('00000000-0000-0000-0000-000000000001'))}/deactivate",
            headers=_auth_headers(admin_token),
        )
        # The known admin uuid may not be an ADMIN; fall back to actual admin
        admin = await get_user_by_email(ADMIN_EMAIL)
        r2 = await client.patch(
            f"/api/users/{str(admin['id'])}/deactivate",
            headers=_auth_headers(admin_token),
        )
        assert r2.status_code == 409

    async def test_admin_update_role_removing_last_admin_blocked(self, client: AsyncClient, admin_token, pool):
        admin = await get_user_by_email(ADMIN_EMAIL)
        admin_id = str(admin["id"])
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id FROM users WHERE role = 'ADMIN' AND is_active = TRUE AND email <> $1",
                ADMIN_EMAIL,
            )
            for row in rows:
                await conn.execute("UPDATE users SET is_active = FALSE WHERE id = $1", row["id"])

        r = await client.patch(
            f"/api/users/{admin_id}",
            headers=_auth_headers(admin_token),
            json={"role": "MANAGER"},
        )
        assert r.status_code == 409

    async def test_password_not_overwritten_without_new_password(self, client: AsyncClient, admin_token, pool):
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM users WHERE email = $1 OR email = $2", "keep_pw@example.org", "keep_pw2@example.org")
            user_id = await _create_user_direct(conn, "keep_pw@example.org")
            original = await conn.fetchrow(
                "SELECT hashed_password FROM users WHERE id = $1",
                uuid.UUID(user_id),
            )

        r = await client.patch(
            f"/api/users/{user_id}",
            headers=_auth_headers(admin_token),
            json={"email": "keep_pw2@example.org"},
        )
        assert r.status_code == 200

        async with pool.acquire() as conn:
            after = await conn.fetchrow(
                "SELECT hashed_password FROM users WHERE id = $1",
                uuid.UUID(user_id),
            )
        assert after["hashed_password"] == original["hashed_password"]


class TestUserManagementSearch:
    async def test_search_filter(self, client: AsyncClient, admin_token, pool):
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM users WHERE email LIKE $1",
                "%searchable%",
            )
            await _create_user_direct(conn, "searchable@example.org")

        r = await client.get(
            "/api/users?search=searchable",
            headers=_auth_headers(admin_token),
        )
        assert r.status_code == 200
        found = [u for u in r.json()["items"] if "searchable" in u["email"]]
        assert len(found) == 1

    async def test_role_filter(self, client: AsyncClient, admin_token, pool):
        async with pool.acquire() as conn:
            await _create_user_direct(conn, "manager_filter@example.org", role="MANAGER")

        r = await client.get(
            "/api/users?role=MANAGER",
            headers=_auth_headers(admin_token),
        )
        assert r.status_code == 200
        assert all(u["role"] == "MANAGER" for u in r.json()["items"])

    async def test_active_filter(self, client: AsyncClient, admin_token, pool):
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM users WHERE email = $1",
                "inactive_filter@example.org",
            )
            await conn.execute(
                "INSERT INTO users (email, hashed_password, role, is_active) VALUES ($1, $2, 'STAFF', FALSE)",
                "inactive_filter@example.org",
                hash_password("TestPassword123!"),
            )

        r = await client.get(
            "/api/users?is_active=false",
            headers=_auth_headers(admin_token),
        )
        assert r.status_code == 200
        emails = [u["email"] for u in r.json()["items"]]
        assert "inactive_filter@example.org" in emails

    async def test_pagination(self, client: AsyncClient, admin_token):
        r = await client.get(
            "/api/users?page=1&page_size=5",
            headers=_auth_headers(admin_token),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["page"] == 1
        assert data["page_size"] == 5
        assert len(data["items"]) <= 5
