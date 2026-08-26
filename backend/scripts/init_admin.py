import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.database import get_pool
from app.core.security import hash_password


async def init_admin() -> None:
    email = os.environ.get("AUTH_INITIAL_ADMIN_EMAIL")
    password = os.environ.get("AUTH_INITIAL_ADMIN_PASSWORD")

    if not email or not password:
        print("ERROR: AUTH_INITIAL_ADMIN_EMAIL and AUTH_INITIAL_ADMIN_PASSWORD must be set.")
        sys.exit(1)

    if len(password) < 8:
        print("ERROR: Password must be at least 8 characters.")
        sys.exit(1)

    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT id FROM users WHERE email = $1", email)
        if existing:
            print(f"Admin user already exists: {email}")
            return

        hashed = hash_password(password)
        await conn.execute(
            "INSERT INTO users (email, hashed_password, role, is_active) VALUES ($1, $2, 'ADMIN', TRUE)",
            email,
            hashed,
        )
        print(f"Admin user created: {email}")


if __name__ == "__main__":
    asyncio.run(init_admin())
