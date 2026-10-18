"""
Development seed data (never used in deployed environments).

Creates a demo user and an admin with known passwords plus a few todos, so a fresh local database is
usable immediately. Refuses to run unless ENVIRONMENT=development. Production bootstrap (the first
admin) is done with `scripts/create_admin.py` instead.

    uv run python scripts/seed_dev.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app import models as _models  # noqa: E402,F401
from app.container import Container  # noqa: E402
from app.core.config import config  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.modules.todos.infrastructure.persistence.models import Todos  # noqa: E402
from app.modules.users.infrastructure.persistence.models import Users  # noqa: E402

DEMO_PASSWORD = "Password123!"
ACCOUNTS = [("demo@example.com", "DEMOUSER", "user"), ("admin@example.com", "ADMINUSR", "admin")]


async def main() -> None:
    if config.ENVIRONMENT != "development":
        sys.exit("Refusing to seed: ENVIRONMENT must be 'development'.")
    db = Container().db()
    async with db.session_scope() as session:
        for email, username, role in ACCOUNTS:
            if (await session.execute(select(Users).where(Users.email == email))).scalar_one_or_none():
                print(f"exists: {email}")
                continue
            user = Users(
                email=email,
                username=username,
                password=hash_password(DEMO_PASSWORD),
                role=role,
                created_by="seed",
                updated_by="seed",
            )
            session.add(user)
            await session.flush()
            for title in ("Try the API docs at /docs", "Upload an attachment", "Archive a finished todo"):
                session.add(Todos(user_id=user.id, title=title, created_by=username, updated_by=username))
            print(f"created: {email} / {DEMO_PASSWORD} ({role})")
    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
