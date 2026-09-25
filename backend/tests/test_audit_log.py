import json
import uuid

import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.services.auth_service import create_access_token_for_user, get_user_by_email


ADMIN_EMAIL = "admin@le-seizieme.local"
ADMIN_PASSWORD = "SecurePassword123!"


def _auth_headers(token: str):
    return {"Authorization": f"Bearer {token}"}


def _parse_detail(value):
    if isinstance(value, str):
        return json.loads(value)
    return value


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


async def _count_audit_log(pool) -> int:
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT COUNT(*) FROM audit_log")


async def _count_audit_log_by_action(pool, action: str) -> int:
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT COUNT(*) FROM audit_log WHERE action = $1", action)


class TestAuditLogCreated:
    async def test_create_user_logs_audit(self, client: AsyncClient, admin_token, pool):
        email = f"audit_create_{uuid.uuid4().hex[:8]}@example.org"
        r = await client.post(
            "/api/users",
            headers=_auth_headers(admin_token),
            json={"email": email, "password": "Password123!", "role": "MANAGER"},
        )
        assert r.status_code == 201

        admin = await get_user_by_email(ADMIN_EMAIL)
        admin_id = str(admin["id"])
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT actor_user_id, target_user_id, action, detail FROM audit_log WHERE action = 'USER_CREATED' ORDER BY created_at DESC LIMIT 1",
            )
        assert row is not None
        assert str(row["actor_user_id"]) == admin_id
        detail = _parse_detail(row["detail"])
        assert detail["email"] == email
        assert detail["role"] == "MANAGER"
        assert str(row["target_user_id"]) == r.json()["id"]

    async def test_create_user_detail_has_no_password(self, client: AsyncClient, admin_token, pool):
        email = f"audit_nopw_{uuid.uuid4().hex[:8]}@example.org"
        r = await client.post(
            "/api/users",
            headers=_auth_headers(admin_token),
            json={"email": email, "password": "Password123!", "role": "STAFF"},
        )
        assert r.status_code == 201

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT detail FROM audit_log WHERE action = 'USER_CREATED' ORDER BY created_at DESC LIMIT 1",
            )
        detail = _parse_detail(row["detail"])
        assert "password" not in detail
        assert "hashed_password" not in detail


class TestAuditLogUpdated:
    async def test_role_update_logs_audit(self, client: AsyncClient, admin_token, pool):
        async with pool.acquire() as conn:
            user_id = await _create_user_direct(conn, "audit_update_role@example.org")

        r = await client.patch(
            f"/api/users/{user_id}",
            headers=_auth_headers(admin_token),
            json={"role": "MANAGER"},
        )
        assert r.status_code == 200

        admin = await get_user_by_email(ADMIN_EMAIL)
        admin_id = str(admin["id"])
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT actor_user_id, target_user_id, action, detail FROM audit_log WHERE action = 'USER_UPDATED' AND target_user_id = $1 ORDER BY created_at DESC LIMIT 1",
                uuid.UUID(user_id),
            )
        assert row is not None
        assert str(row["actor_user_id"]) == admin_id
        assert str(row["target_user_id"]) == user_id
        detail = _parse_detail(row["detail"])
        assert "role" in detail["changed_fields"]
        assert detail["changes"]["role"]["old"] == "STAFF"
        assert detail["changes"]["role"]["new"] == "MANAGER"

    async def test_email_update_logs_audit(self, client: AsyncClient, admin_token, pool):
        suffix = uuid.uuid4().hex[:8]
        async with pool.acquire() as conn:
            user_id = await _create_user_direct(conn, f"audit_email_old_{suffix}@example.org")

        r = await client.patch(
            f"/api/users/{user_id}",
            headers=_auth_headers(admin_token),
            json={"email": f"audit_email_new_{suffix}@example.org"},
        )
        assert r.status_code == 200

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT actor_user_id, target_user_id, action, detail FROM audit_log WHERE action = 'USER_UPDATED' AND target_user_id = $1 ORDER BY created_at DESC LIMIT 1",
                uuid.UUID(user_id),
            )
        assert row is not None
        detail = _parse_detail(row["detail"])
        assert "email" in detail["changed_fields"]
        assert detail["changes"]["email"]["old"] == f"audit_email_old_{suffix}@example.org"
        assert detail["changes"]["email"]["new"] == f"audit_email_new_{suffix}@example.org"

    async def test_password_update_logs_audit(self, client: AsyncClient, admin_token, pool):
        async with pool.acquire() as conn:
            user_id = await _create_user_direct(conn, "audit_update_pw@example.org")

        r = await client.patch(
            f"/api/users/{user_id}",
            headers=_auth_headers(admin_token),
            json={"password": "NewPassword123!"},
        )
        assert r.status_code == 200

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT detail FROM audit_log WHERE action = 'USER_UPDATED' AND target_user_id = $1 ORDER BY created_at DESC LIMIT 1",
                uuid.UUID(user_id),
            )
        detail = _parse_detail(row["detail"])
        assert "password" in detail["changed_fields"]
        assert detail["changes"]["password"] == {"changed": True}
        assert "password" not in str(detail.get("changes", {}).get("password", {}))
        assert "$argon2" not in json.dumps(detail)

    async def test_is_active_update_logs_audit(self, client: AsyncClient, admin_token, pool):
        async with pool.acquire() as conn:
            user_id = await _create_user_direct(conn, "audit_update_active@example.org")

        r = await client.patch(
            f"/api/users/{user_id}",
            headers=_auth_headers(admin_token),
            json={"is_active": False},
        )
        assert r.status_code == 200

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT detail FROM audit_log WHERE action = 'USER_UPDATED' AND target_user_id = $1 ORDER BY created_at DESC LIMIT 1",
                uuid.UUID(user_id),
            )
        detail = _parse_detail(row["detail"])
        assert "is_active" in detail["changed_fields"]
        assert detail["changes"]["is_active"]["old"] is True
        assert detail["changes"]["is_active"]["new"] is False

    async def test_multiple_field_update_logs_all_changes(self, client: AsyncClient, admin_token, pool):
        suffix = uuid.uuid4().hex[:8]
        async with pool.acquire() as conn:
            user_id = await _create_user_direct(conn, f"audit_multi_old_{suffix}@example.org", role="STAFF")

        r = await client.patch(
            f"/api/users/{user_id}",
            headers=_auth_headers(admin_token),
            json={"email": f"audit_multi_new_{suffix}@example.org", "role": "MANAGER", "is_active": False},
        )
        assert r.status_code == 200

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT detail FROM audit_log WHERE action = 'USER_UPDATED' AND target_user_id = $1 ORDER BY created_at DESC LIMIT 1",
                uuid.UUID(user_id),
            )
        detail = _parse_detail(row["detail"])
        assert set(detail["changed_fields"]) == {"email", "role", "is_active"}
        assert detail["changes"]["email"]["old"] == f"audit_multi_old_{suffix}@example.org"
        assert detail["changes"]["role"]["old"] == "STAFF"
        assert detail["changes"]["is_active"]["old"] is True

    async def test_no_op_update_no_audit_entry(self, client: AsyncClient, admin_token, pool):
        async with pool.acquire() as conn:
            user_id = await _create_user_direct(conn, "audit_noop@example.org", role="STAFF")
            before = await conn.fetchval("SELECT COUNT(*) FROM audit_log WHERE action = 'USER_UPDATED'")

        r = await client.patch(
            f"/api/users/{user_id}",
            headers=_auth_headers(admin_token),
            json={"role": "STAFF"},
        )
        assert r.status_code == 200

        async with pool.acquire() as conn:
            after = await conn.fetchval("SELECT COUNT(*) FROM audit_log WHERE action = 'USER_UPDATED'")
        assert before == after

    async def test_no_op_update_with_no_fields(self, client: AsyncClient, admin_token, pool):
        async with pool.acquire() as conn:
            user_id = await _create_user_direct(conn, "audit_empty_patch@example.org")
            before = await _count_audit_log_by_action(pool, "USER_UPDATED")

        r = await client.patch(
            f"/api/users/{user_id}",
            headers=_auth_headers(admin_token),
            json={},
        )
        assert r.status_code == 200

        after = await _count_audit_log_by_action(pool, "USER_UPDATED")
        assert before == after


class TestAuditLogDeactivated:
    async def test_deactivate_user_logs_audit(self, client: AsyncClient, admin_token, pool):
        async with pool.acquire() as conn:
            user_id = await _create_user_direct(conn, "audit_deact@example.org")

        r = await client.patch(
            f"/api/users/{user_id}/deactivate",
            headers=_auth_headers(admin_token),
        )
        assert r.status_code == 200

        admin = await get_user_by_email(ADMIN_EMAIL)
        admin_id = str(admin["id"])
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT actor_user_id, target_user_id, action, detail FROM audit_log WHERE action = 'USER_DEACTIVATED' AND target_user_id = $1 ORDER BY created_at DESC LIMIT 1",
                uuid.UUID(user_id),
            )
        assert row is not None
        assert str(row["actor_user_id"]) == admin_id
        assert str(row["target_user_id"]) == user_id
        detail = _parse_detail(row["detail"])
        assert detail["email"] == "audit_deact@example.org"


class TestAuditLogRollback:
    async def test_audit_not_logged_on_duplicate_email(self, client: AsyncClient, admin_token, pool):
        async with pool.acquire() as conn:
            await _create_user_direct(conn, "dup_audit@example.org")
            before = await _count_audit_log(pool)

        r = await client.post(
            "/api/users",
            headers=_auth_headers(admin_token),
            json={"email": "dup_audit@example.org", "password": "Password123!", "role": "STAFF"},
        )
        assert r.status_code == 409

        after = await _count_audit_log(pool)
        assert before == after

    async def test_audit_not_logged_on_deactivate_self(self, client: AsyncClient, admin_token, pool):
        admin = await get_user_by_email(ADMIN_EMAIL)
        admin_id = str(admin["id"])
        before = await _count_audit_log_by_action(pool, "USER_DEACTIVATED")

        r = await client.patch(
            f"/api/users/{admin_id}/deactivate",
            headers=_auth_headers(admin_token),
        )
        assert r.status_code == 409

        after = await _count_audit_log_by_action(pool, "USER_DEACTIVATED")
        assert before == after

    async def test_audit_not_logged_on_update_unknown_user(self, client: AsyncClient, admin_token, pool):
        before = await _count_audit_log_by_action(pool, "USER_UPDATED")

        r = await client.patch(
            "/api/users/00000000-0000-0000-0000-000000000999",
            headers=_auth_headers(admin_token),
            json={"role": "MANAGER"},
        )
        assert r.status_code == 404

        after = await _count_audit_log_by_action(pool, "USER_UPDATED")
        assert before == after

    async def test_audit_not_logged_on_duplicate_email_update(self, client: AsyncClient, admin_token, pool):
        async with pool.acquire() as conn:
            await _create_user_direct(conn, "existing_dup@example.org")
            target_id = await _create_user_direct(conn, "target_dup@example.org")
            before = await _count_audit_log_by_action(pool, "USER_UPDATED")

        r = await client.patch(
            f"/api/users/{target_id}",
            headers=_auth_headers(admin_token),
            json={"email": "existing_dup@example.org"},
        )
        assert r.status_code == 409

        after = await _count_audit_log_by_action(pool, "USER_UPDATED")
        assert before == after

    async def test_audit_not_logged_on_deactivate_last_admin(self, client: AsyncClient, admin_token, pool):
        admin = await get_user_by_email(ADMIN_EMAIL)
        admin_id = str(admin["id"])
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id FROM users WHERE role = 'ADMIN' AND is_active = TRUE AND email <> $1",
                ADMIN_EMAIL,
            )
            for row in rows:
                await conn.execute("UPDATE users SET is_active = FALSE WHERE id = $1", row["id"])

        before = await _count_audit_log_by_action(pool, "USER_DEACTIVATED")

        r = await client.patch(
            f"/api/users/{admin_id}/deactivate",
            headers=_auth_headers(admin_token),
        )
        assert r.status_code == 409

        after = await _count_audit_log_by_action(pool, "USER_DEACTIVATED")
        assert before == after


class TestAuditLogAuthorization:
    async def test_staff_update_returns_403_no_audit(self, client: AsyncClient, staff_token, pool):
        async with pool.acquire() as conn:
            user_id = await _create_user_direct(conn, "audit_403@example.org")
            before = await _count_audit_log_by_action(pool, "USER_UPDATED")

        r = await client.patch(
            f"/api/users/{user_id}",
            headers=_auth_headers(staff_token),
            json={"role": "MANAGER"},
        )
        assert r.status_code == 403

        after = await _count_audit_log_by_action(pool, "USER_UPDATED")
        assert before == after

    async def test_staff_create_returns_403_no_audit(self, client: AsyncClient, staff_token, pool):
        before = await _count_audit_log_by_action(pool, "USER_CREATED")

        r = await client.post(
            "/api/users",
            headers=_auth_headers(staff_token),
            json={"email": "audit_403_create@example.org", "password": "Password123!", "role": "STAFF"},
        )
        assert r.status_code == 403

        after = await _count_audit_log_by_action(pool, "USER_CREATED")
        assert before == after

    async def test_staff_deactivate_returns_403_no_audit(self, client: AsyncClient, staff_token, pool):
        async with pool.acquire() as conn:
            user_id = await _create_user_direct(conn, "audit_403_deact@example.org")
            before = await _count_audit_log_by_action(pool, "USER_DEACTIVATED")

        r = await client.patch(
            f"/api/users/{user_id}/deactivate",
            headers=_auth_headers(staff_token),
        )
        assert r.status_code == 403

        after = await _count_audit_log_by_action(pool, "USER_DEACTIVATED")
        assert before == after

    async def test_unauthenticated_create_returns_401_no_audit(self, client: AsyncClient, pool):
        before = await _count_audit_log_by_action(pool, "USER_CREATED")

        r = await client.post(
            "/api/users",
            json={"email": "audit_401_create@example.org", "password": "Password123!", "role": "STAFF"},
        )
        assert r.status_code == 401

        after = await _count_audit_log_by_action(pool, "USER_CREATED")
        assert before == after

    async def test_unauthenticated_update_returns_401_no_audit(self, client: AsyncClient, pool):
        async with pool.acquire() as conn:
            user_id = await _create_user_direct(conn, "audit_401_update@example.org")
            before = await _count_audit_log_by_action(pool, "USER_UPDATED")

        r = await client.patch(
            f"/api/users/{user_id}",
            json={"role": "MANAGER"},
        )
        assert r.status_code == 401

        after = await _count_audit_log_by_action(pool, "USER_UPDATED")
        assert before == after

    async def test_unauthenticated_deactivate_returns_401_no_audit(self, client: AsyncClient, pool):
        async with pool.acquire() as conn:
            user_id = await _create_user_direct(conn, "audit_401_deact@example.org")
            before = await _count_audit_log_by_action(pool, "USER_DEACTIVATED")

        r = await client.patch(
            f"/api/users/{user_id}/deactivate",
        )
        assert r.status_code == 401

        after = await _count_audit_log_by_action(pool, "USER_DEACTIVATED")
        assert before == after


class TestAuditLogReadAuthorization:
    async def test_unauthenticated_get_audit_log_returns_401(self, client: AsyncClient):
        r = await client.get("/api/audit-log")
        assert r.status_code == 401

    async def test_route_ordering_audit_log_not_caught_by_users_dynamic(self, client: AsyncClient, admin_token):
        r = await client.get("/api/audit-log", headers=_auth_headers(admin_token))
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data

    async def test_manager_get_audit_log_returns_403(self, client: AsyncClient, manager_token):
        r = await client.get("/api/audit-log", headers=_auth_headers(manager_token))
        assert r.status_code == 403

    async def test_staff_get_audit_log_returns_403(self, client: AsyncClient, staff_token):
        r = await client.get("/api/audit-log", headers=_auth_headers(staff_token))
        assert r.status_code == 403


class TestAuditLogReadPagination:
    async def test_admin_can_list_audit_log(self, client: AsyncClient, admin_token):
        r = await client.get("/api/audit-log", headers=_auth_headers(admin_token))
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        assert isinstance(data["items"], list)

    async def test_pagination_defaults(self, client: AsyncClient, admin_token):
        r = await client.get("/api/audit-log", headers=_auth_headers(admin_token))
        assert r.status_code == 200
        data = r.json()
        assert data["page"] == 1
        assert data["page_size"] == 20

    async def test_page_size_respected(self, client: AsyncClient, admin_token):
        r = await client.get("/api/audit-log?page_size=3", headers=_auth_headers(admin_token))
        assert r.status_code == 200
        data = r.json()
        assert data["page_size"] == 3
        assert len(data["items"]) <= 3

    async def test_page_respected(self, client: AsyncClient, admin_token, pool):
        await _seed_audit_records(pool, count=5)
        r = await client.get("/api/audit-log?page=2&page_size=2", headers=_auth_headers(admin_token))
        assert r.status_code == 200
        data = r.json()
        assert data["page"] == 2
        assert data["page_size"] == 2
        assert len(data["items"]) <= 2

    async def test_page_beyond_total_returns_empty(self, client: AsyncClient, admin_token, pool):
        await _seed_audit_records(pool, count=2)
        r = await client.get("/api/audit-log?page=999&page_size=10", headers=_auth_headers(admin_token))
        assert r.status_code == 200
        data = r.json()
        assert data["items"] == []
        assert data["total"] >= 2
        assert data["total_pages"] >= 1

    async def test_page_size_below_minimum_rejected(self, client: AsyncClient, admin_token):
        r = await client.get("/api/audit-log?page_size=0", headers=_auth_headers(admin_token))
        assert r.status_code == 422

    async def test_page_size_above_maximum_rejected(self, client: AsyncClient, admin_token):
        r = await client.get("/api/audit-log?page_size=200", headers=_auth_headers(admin_token))
        assert r.status_code == 422

    async def test_total_pages_calculation(self, client: AsyncClient, admin_token, pool):
        await _seed_audit_records(pool, count=3)
        r = await client.get("/api/audit-log?page=1&page_size=2", headers=_auth_headers(admin_token))
        assert r.status_code == 200
        data = r.json()
        assert data["total_pages"] == max(1, -(-data["total"] // 2))


class TestAuditLogReadFiltering:
    async def test_filter_by_action(self, client: AsyncClient, admin_token, pool):
        await _seed_audit_records(pool, count=3, actions=["USER_CREATED", "USER_UPDATED"])
        r = await client.get("/api/audit-log?action=USER_CREATED", headers=_auth_headers(admin_token))
        assert r.status_code == 200
        data = r.json()
        assert all(item["action"] == "USER_CREATED" for item in data["items"])

    async def test_filter_by_actor_user_id(self, client: AsyncClient, admin_token, pool):
        admin = await get_user_by_email(ADMIN_EMAIL)
        admin_id = str(admin["id"])
        await _seed_audit_records(pool, count=3, actions=["USER_CREATED"], actor_id=admin_id)
        r = await client.get(f"/api/audit-log?actor_user_id={admin_id}", headers=_auth_headers(admin_token))
        assert r.status_code == 200
        data = r.json()
        assert all(item["actor_user_id"] == admin_id for item in data["items"])

    async def test_filter_by_target_user_id(self, client: AsyncClient, admin_token, pool):
        async with pool.acquire() as conn:
            target_id = await _create_user_direct(conn, "audit_target@example.org")
        admin = await get_user_by_email(ADMIN_EMAIL)
        admin_id = str(admin["id"])
        await _seed_audit_records(pool, count=3, actions=["USER_CREATED"], actor_id=admin_id, target_id=target_id)
        r = await client.get(f"/api/audit-log?target_user_id={target_id}", headers=_auth_headers(admin_token))
        assert r.status_code == 200
        data = r.json()
        assert all(item["target_user_id"] == target_id for item in data["items"])

    async def test_filter_by_created_after(self, client: AsyncClient, admin_token, pool):
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(hours=1)
        await _seed_audit_records(pool, count=2)
        r = await client.get(
            f"/api/audit-log?created_after={cutoff.isoformat()}",
            headers=_auth_headers(admin_token),
        )
        assert r.status_code == 200
        data = r.json()
        for item in data["items"]:
            item_dt = datetime.fromisoformat(item["created_at"])
            assert item_dt >= cutoff

    async def test_filter_by_created_before(self, client: AsyncClient, admin_token, pool):
        from datetime import datetime, timedelta
        cutoff = datetime.now() + timedelta(hours=1)
        await _seed_audit_records(pool, count=2)
        r = await client.get(
            f"/api/audit-log?created_before={cutoff.isoformat()}",
            headers=_auth_headers(admin_token),
        )
        assert r.status_code == 200
        data = r.json()
        for item in data["items"]:
            item_dt = datetime.fromisoformat(item["created_at"])
            assert item_dt <= cutoff

    async def test_combined_filters(self, client: AsyncClient, admin_token, pool):
        admin = await get_user_by_email(ADMIN_EMAIL)
        admin_id = str(admin["id"])
        await _seed_audit_records(pool, count=5, actions=["USER_CREATED", "USER_UPDATED"], actor_id=admin_id)
        r = await client.get(
            f"/api/audit-log?action=USER_CREATED&actor_user_id={admin_id}",
            headers=_auth_headers(admin_token),
        )
        assert r.status_code == 200
        data = r.json()
        assert all(item["action"] == "USER_CREATED" and item["actor_user_id"] == admin_id for item in data["items"])


class TestAuditLogReadContent:
    async def test_audit_log_item_fields(self, client: AsyncClient, admin_token, pool):
        admin = await get_user_by_email(ADMIN_EMAIL)
        admin_id = str(admin["id"])
        async with pool.acquire() as conn:
            target_id = await _create_user_direct(conn, "content_check@example.org")
        await _seed_audit_records(pool, count=1, actions=["USER_CREATED"], actor_id=admin_id, target_id=target_id)
        r = await client.get("/api/audit-log?page_size=1", headers=_auth_headers(admin_token))
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) >= 1
        item = data["items"][0]
        assert "id" in item
        assert "actor_user_id" in item
        assert "target_user_id" in item
        assert "action" in item
        assert "detail" in item
        assert "created_at" in item
        assert "actor_email" in item
        assert "target_email" in item

    async def test_audit_log_detail_is_object(self, client: AsyncClient, admin_token, pool):
        admin = await get_user_by_email(ADMIN_EMAIL)
        admin_id = str(admin["id"])
        async with pool.acquire() as conn:
            target_id = await _create_user_direct(conn, "detail_check@example.org")
        await _seed_audit_records(pool, count=1, actions=["USER_CREATED"], actor_id=admin_id, target_id=target_id)
        r = await client.get("/api/audit-log?page_size=1&action=USER_CREATED", headers=_auth_headers(admin_token))
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) >= 1
        detail = data["items"][0]["detail"]
        assert isinstance(detail, dict)

    async def test_audit_log_actor_email_populated(self, client: AsyncClient, admin_token, pool):
        admin = await get_user_by_email(ADMIN_EMAIL)
        admin_id = str(admin["id"])
        async with pool.acquire() as conn:
            target_id = await _create_user_direct(conn, "actor_email_check@example.org")
        await _seed_audit_records(pool, count=1, actions=["USER_CREATED"], actor_id=admin_id, target_id=target_id)
        r = await client.get(
            f"/api/audit-log?action=USER_CREATED&actor_user_id={admin_id}",
            headers=_auth_headers(admin_token),
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) >= 1
        assert data["items"][0]["actor_email"] == ADMIN_EMAIL

    async def test_audit_log_target_email_populated(self, client: AsyncClient, admin_token, pool):
        admin = await get_user_by_email(ADMIN_EMAIL)
        admin_id = str(admin["id"])
        target_email = "target_email_check@example.org"
        async with pool.acquire() as conn:
            target_id = await _create_user_direct(conn, target_email)
        await _seed_audit_records(pool, count=1, actions=["USER_CREATED"], actor_id=admin_id, target_id=target_id)
        r = await client.get(
            f"/api/audit-log?action=USER_CREATED&target_user_id={target_id}",
            headers=_auth_headers(admin_token),
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) >= 1
        assert data["items"][0]["target_email"] == target_email

    async def test_invalid_action_filter_returns_empty(self, client: AsyncClient, admin_token):
        r = await client.get("/api/audit-log?action=NONEXISTENT_ACTION", headers=_auth_headers(admin_token))
        assert r.status_code == 200
        data = r.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_invalid_target_user_id_filter_returns_empty(self, client: AsyncClient, admin_token):
        r = await client.get(
            "/api/audit-log?target_user_id=00000000-0000-0000-0000-000000000099",
            headers=_auth_headers(admin_token),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["items"] == []
        assert data["total"] == 0


class TestAuditLogSecurity:
    async def test_no_password_in_audit_log_detail(self, client: AsyncClient, admin_token):
        r = await client.get("/api/audit-log", headers=_auth_headers(admin_token))
        assert r.status_code == 200
        data = r.json()
        for item in data["items"]:
            detail_str = json.dumps(item.get("detail") or {})
            assert "password" not in detail_str
            assert "hashed_password" not in detail_str

    async def test_audit_log_not_exposed_to_non_admins(self, client: AsyncClient, manager_token, staff_token):
        for token in [manager_token, staff_token]:
            r = await client.get("/api/audit-log", headers=_auth_headers(token))
            assert r.status_code == 403


async def _seed_audit_records(pool, count=1, actions=None, actor_id=None, target_id=None):
    if actions is None:
        actions = ["USER_CREATED"]
    admin = await get_user_by_email(ADMIN_EMAIL)
    act_id = actor_id or str(admin["id"])
    async with pool.acquire() as conn:
        for i in range(count):
            act = actions[i % len(actions)]
            await conn.execute(
                """
                INSERT INTO audit_log (actor_user_id, target_user_id, action, detail)
                VALUES ($1, $2, $3, $4::jsonb)
                """,
                act_id,
                target_id,
                act,
                json.dumps({"test_index": i, "action": act}),
            )