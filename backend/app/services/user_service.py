from datetime import datetime
from typing import Any

import asyncpg
from fastapi import HTTPException, status

from app.core.database import get_pool
from app.core.security import hash_password
from app.models.users import ALLOWED_ROLES


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _format_dt(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    if value is None:
        return None
    return str(value)


async def list_users(
    search: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 10,
) -> tuple[list[dict[str, Any]], int]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        where_clauses = []
        params: list[Any] = []
        idx = 1

        if search:
            where_clauses.append(f"email ILIKE ${idx}")
            params.append(f"%{search}%")
            idx += 1

        if role:
            if role not in ALLOWED_ROLES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Rôle invalide.",
                )
            where_clauses.append(f"role = ${idx}")
            params.append(role)
            idx += 1

        if is_active is not None:
            where_clauses.append(f"is_active = ${idx}")
            params.append(is_active)
            idx += 1

        where_sql = " AND ".join(where_clauses)
        if where_sql:
            where_sql = f"WHERE {where_sql}"

        total_row = await conn.fetchrow(
            f"SELECT COUNT(*) AS total FROM users {where_sql}",
            *params,
        )
        total = total_row["total"] if total_row else 0

        offset = (page - 1) * page_size
        order = "ORDER BY email ASC, created_at ASC"
        rows = await conn.fetch(
            f"""
            SELECT id, email, role, is_active, created_at, updated_at
            FROM users
            {where_sql}
            {order}
            LIMIT ${idx} OFFSET ${idx + 1}
            """,
            *params,
            page_size,
            offset,
        )

        items = [{
            "id": str(r["id"]),
            "email": r["email"],
            "role": r["role"],
            "is_active": bool(r["is_active"]),
            "created_at": _format_dt(r["created_at"]),
            "updated_at": _format_dt(r["updated_at"]),
        } for r in rows]

        return items, total


async def get_user(user_id: str) -> dict[str, Any] | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, role, is_active, created_at, updated_at FROM users WHERE id = $1",
            user_id,
        )
        if not row:
            return None
        return {
            "id": str(row["id"]),
            "email": row["email"],
            "role": row["role"],
            "is_active": bool(row["is_active"]),
            "created_at": _format_dt(row["created_at"]),
            "updated_at": _format_dt(row["updated_at"]),
        }


async def create_user(data: dict[str, Any]) -> dict[str, Any]:
    email = _normalize_email(data["email"])
    role = data.get("role", "STAFF")
    is_active = data.get("is_active", True)

    if role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rôle invalide.",
        )

    if not data.get("password"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le mot de passe est requis.",
        )

    password = data["password"]
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le mot de passe doit contenir au moins 8 caractères.",
        )

    hashed = hash_password(password)

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            existing = await conn.fetchrow(
                "SELECT id FROM users WHERE email = $1",
                email,
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Un utilisateur avec cet email existe déjà.",
                )

            row = await conn.fetchrow(
                """
                INSERT INTO users (email, hashed_password, role, is_active)
                VALUES ($1, $2, $3, $4)
                RETURNING id, email, role, is_active, created_at, updated_at
                """,
                email,
                hashed,
                role,
                is_active,
            )
            return {
                "id": str(row["id"]),
                "email": row["email"],
                "role": row["role"],
                "is_active": bool(row["is_active"]),
                "created_at": _format_dt(row["created_at"]),
                "updated_at": _format_dt(row["updated_at"]),
            }


async def count_active_admins(conn, exclude_user_id: str | None = None) -> int:
    params: list[Any] = []
    idx = 1
    where = "role = 'ADMIN' AND is_active = TRUE"
    if exclude_user_id is not None:
        where += f" AND id <> ${idx}"
        params.append(exclude_user_id)
    result = await conn.fetchval(
        f"SELECT COUNT(*) FROM users WHERE {where}",
        *params,
    )
    return result or 0


async def update_user(user_id: str, data: dict[str, Any]) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            current = await conn.fetchrow(
                "SELECT id, email, role, is_active FROM users WHERE id = $1",
                user_id,
            )
            if not current:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")

            set_clauses = []
            params: list[Any] = []
            idx = 1

            if "email" in data and data["email"] is not None:
                new_email = _normalize_email(data["email"])
                conflict = await conn.fetchrow(
                    "SELECT id FROM users WHERE email = $1 AND id <> $2",
                    new_email,
                    user_id,
                )
                if conflict:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Un utilisateur avec cet email existe déjà.",
                    )
                set_clauses.append(f"email = ${idx}")
                params.append(new_email)
                idx += 1

            if "role" in data and data["role"] is not None:
                role_value = data["role"]
                if role_value not in ALLOWED_ROLES:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Rôle invalide.",
                    )
                if role_value != "ADMIN" and current["role"] == "ADMIN" and current["is_active"]:
                    other_admins = await count_active_admins(conn, exclude_user_id=user_id)
                    if other_admins < 1:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="Impossible de retirer le rôle ADMIN du dernier administrateur actif.",
                        )
                set_clauses.append(f"role = ${idx}")
                params.append(role_value)
                idx += 1

            if "password" in data and data["password"] is not None:
                password = data["password"]
                if len(password) < 8:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Le mot de passe doit contenir au moins 8 caractères.",
                    )
                set_clauses.append(f"hashed_password = ${idx}")
                params.append(hash_password(password))
                idx += 1

            if "is_active" in data and data["is_active"] is not None:
                is_active = bool(data["is_active"])
                if not is_active and current["role"] == "ADMIN":
                    other_admins = await count_active_admins(conn, exclude_user_id=user_id)
                    if other_admins < 1:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="Impossible de désactiver le dernier administrateur actif.",
                        )
                set_clauses.append(f"is_active = ${idx}")
                params.append(is_active)
                idx += 1

            if not set_clauses:
                row = await conn.fetchrow(
                    "SELECT id, email, role, is_active, created_at, updated_at FROM users WHERE id = $1",
                    user_id,
                )
            else:
                set_clauses.append("updated_at = NOW()")
                params.append(user_id)
                row = await conn.fetchrow(
                    f"""
                    UPDATE users
                    SET {', '.join(set_clauses)}
                    WHERE id = ${idx}
                    RETURNING id, email, role, is_active, created_at, updated_at
                    """,
                    *params,
                )

            return {
                "id": str(row["id"]),
                "email": row["email"],
                "role": row["role"],
                "is_active": bool(row["is_active"]),
                "created_at": _format_dt(row["created_at"]),
                "updated_at": _format_dt(row["updated_at"]),
            }


async def deactivate_user(user_id: str, actor_id: str) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            current = await conn.fetchrow(
                "SELECT id, email, role, is_active FROM users WHERE id = $1",
                user_id,
            )
            if not current:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")

            if str(current["id"]) == str(actor_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Vous ne pouvez pas désactiver votre propre compte.",
                )

            if current["role"] == "ADMIN" and current["is_active"]:
                other_admins = await count_active_admins(conn, exclude_user_id=user_id)
                if other_admins < 1:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Impossible de désactiver le dernier administrateur actif.",
                    )

            row = await conn.fetchrow(
                """
                UPDATE users
                SET is_active = FALSE, updated_at = NOW()
                WHERE id = $1
                RETURNING id, email, role, is_active, created_at, updated_at
                """,
                user_id,
            )
            return {
                "id": str(row["id"]),
                "email": row["email"],
                "role": row["role"],
                "is_active": bool(row["is_active"]),
                "created_at": _format_dt(row["created_at"]),
                "updated_at": _format_dt(row["updated_at"]),
                "message": "Utilisateur désactivé avec succès.",
            }
