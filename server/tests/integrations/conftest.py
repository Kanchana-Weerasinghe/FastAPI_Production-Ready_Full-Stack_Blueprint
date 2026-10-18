from collections.abc import AsyncGenerator

import pytest

from app.main import db


@pytest.fixture(autouse=True)
async def isolated_app_transaction() -> AsyncGenerator[None, None]:
    """
    Runs each integration test inside an outer transaction that is rolled back afterwards.

    The app's sessions are bound to that connection with `create_savepoint`, so every
    request-level commit only releases a SAVEPOINT and no test can leak data into the next.
    """
    session_factory = db._session_factory
    async with db._engine.connect() as connection:
        transaction = await connection.begin()
        session_factory.configure(bind=connection, join_transaction_mode="create_savepoint")
        try:
            yield
        finally:
            session_factory.configure(bind=db._engine, join_transaction_mode="conservative_savepoint")
            await transaction.rollback()
