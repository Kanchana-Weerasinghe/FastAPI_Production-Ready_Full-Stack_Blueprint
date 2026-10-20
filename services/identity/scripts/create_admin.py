"""
Production bootstrap: create the first administrator, or promote an existing account.

Run once per environment as a one-off job (e.g. `kubectl run` / ECS task) with the password supplied
through the environment, never on the command line or in shell history:

    ADMIN_EMAIL=ops@example.com ADMIN_PASSWORD=... uv run python scripts/create_admin.py

The action is recorded in the audit log.
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app import models as _models  # noqa: E402,F401
from app.container import Container  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.modules.auth.schemas import SignUp  # noqa: E402
from app.modules.auth.service import generate_username  # noqa: E402
from app.modules.users.infrastructure.persistence.models import Users  # noqa: E402
from app.modules.users.service import Role  # noqa: E402


async def main() -> None:
    email, password = os.environ.get("ADMIN_EMAIL"), os.environ.get("ADMIN_PASSWORD")
    if not email:
        sys.exit("Set ADMIN_EMAIL (and ADMIN_PASSWORD to create a new account).")
    container = Container()
    db = container.db()
    async with db.session_scope() as session:
        user = (await session.execute(select(Users).where(Users.email == email))).scalar_one_or_none()
        if user is None:
            if not password:
                sys.exit("No account with that email: set ADMIN_PASSWORD to create it.")
            SignUp(email=email, password=password)  # enforce the password policy
            username = generate_username()
            user = Users(
                email=email,
                username=username,
                password=hash_password(password),
                role=Role.ADMIN,
                created_by="bootstrap",
                updated_by="bootstrap",
            )
            session.add(user)
            action = "admin.bootstrap.created"
        else:
            user.role = Role.ADMIN
            action = "admin.bootstrap.promoted"
        await session.flush()
        await container.audit.service().record(action, actor_id=user.id, resource_type="user", resource_id=user.id)
    print(f"{action}: {email}")
    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
