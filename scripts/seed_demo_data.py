"""CLI Script to Idempotently Seed Verified Manipur Pilot Scholarship Schemes."""

import asyncio

from src.core.database import close_db_engine, get_session_factory
from src.core.logging import get_logger, setup_logging
from src.modules.catalog.infrastructure.seed_data import seed_pilot_schemes

logger = get_logger("seed_demo_data")


async def main() -> None:
    setup_logging()
    logger.info("Connecting to database to seed verified Manipur pilot schemes...")
    session_factory = get_session_factory()
    async with session_factory() as session:
        count = await seed_pilot_schemes(session)
        logger.info("Successfully seeded %d new schemes (or verified already present).", count)
    await close_db_engine()


if __name__ == "__main__":
    asyncio.run(main())
