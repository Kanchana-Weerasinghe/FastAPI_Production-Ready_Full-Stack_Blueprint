"""
Verification script to ensure database readiness before application startup.

This script is typically executed by Docker Compose as a 'pre-start' step to
prevent the FastAPI app from starting before the database is fully reachable.
"""

import asyncio
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

from app.core.config import config
from app.core.logging import logger, setup_logging

setup_logging()


async def check_db_connection() -> bool:
    """Attempts a single asynchronous connection to the database to verify reachability."""
    try:
        logger.info("creating_async_engine")
        engine = create_async_engine(config.SQLALCHEMY_DATABASE_URI)
        async with engine.connect() as conn:
            await conn.execute(select(1))
        logger.info("connection_successful")
        await engine.dispose()
        return True
    except Exception as e:
        logger.error("database_connection_failed", error=str(e))
        return False


async def main() -> None:
    """
    Main loop that retries the database connection until it succeeds or
    the maximum number of attempts is reached.
    """
    logger.info("checking_database_connection")
    max_retries = 30
    retry_interval = 2
    for i in range(max_retries):
        if await check_db_connection():
            logger.info("database_connection_successful")
            sys.exit(0)
        logger.warning("waiting_for_database", attempt=i + 1, max_retries=max_retries, retry_interval=retry_interval)
        await asyncio.sleep(retry_interval)
    logger.error("database_connection_failed")
    sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
