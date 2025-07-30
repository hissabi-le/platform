import asyncio

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from api.src.models import Base, Organisation, User


@pytest.fixture()
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_crud_models(session: AsyncSession) -> None:
    org = Organisation(name="test")
    session.add(org)
    await session.commit()
    await session.refresh(org)

    user = User(org_id=org.id, email="u@example.com", hashed_password="x", role="user")
    session.add(user)
    await session.commit()
    await session.refresh(user)

    res = await session.get(User, user.id)
    assert res.email == "u@example.com"
