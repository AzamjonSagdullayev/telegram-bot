import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.config import settings

log = logging.getLogger(__name__)

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db():
    from app.models import Base
    async with engine.begin() as conn:
        # Create all tables that do not exist yet
        await conn.run_sync(Base.metadata.create_all)

        # Non-destructive migrations for existing tables:
        # Safely add any new columns to service_orders if table already existed
        try:
            await conn.execute(text("ALTER TABLE service_orders ADD COLUMN IF NOT EXISTS note TEXT DEFAULT '';"))
            await conn.execute(text("ALTER TABLE service_orders ADD COLUMN IF NOT EXISTS handled_by_admin BIGINT;"))
            await conn.execute(text("ALTER TABLE service_orders ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;"))
        except Exception as exc:
            log.warning("Migration note/handled_by_admin check warning: %s", exc)

    log.info("Database schema verified and up to date.")
