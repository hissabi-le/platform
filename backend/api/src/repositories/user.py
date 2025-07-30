from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User
from ..schemas import UserCreate


class UserRepo:
    async def get_by_email(self, session: AsyncSession, email: str) -> User | None:
        result = await session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, session: AsyncSession, user_in: UserCreate) -> User:
        user = User(**user_in.model_dump())
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    async def update_role(self, session: AsyncSession, user: User, new_role: str) -> User:
        user.role = new_role
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
