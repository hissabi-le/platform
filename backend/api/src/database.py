import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

# your DB URL (make sure DATABASE_URL is set in env)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:secret@db:5432/postgres",
)

# async engine & session factory
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# this is the Base your models import
Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """fastapi dependency that yields an async session."""
    async with async_session() as session:
        yield session
