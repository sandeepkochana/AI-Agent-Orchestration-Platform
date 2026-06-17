from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    from models import agent, workflow, execution, message, thread_message  # noqa: ensure models registered
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Idempotent column migrations for SQLite (avoids needing Alembic for simple additions)
        for stmt in [
            "ALTER TABLE agents ADD COLUMN interaction_rules JSON DEFAULT '{}'",
            "ALTER TABLE agents ADD COLUMN skills JSON DEFAULT '[]'",
        ]:
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass  # column already exists — safe to ignore
