# backend/api/src/repositories/user.py
from __future__ import annotations
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext

from ..models import User, Organisation

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALLOWED_ROLES = {"user", "admin"}


def hash_password(p: str) -> str:
    return _pwd.hash(p)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _pwd.verify(plain, hashed)
    except Exception:
        return False


class UserRepo:
    # ---------- reads ----------
    async def by_email(self, session: AsyncSession, email: str) -> Optional[User]:
        email_norm = (email or "").strip().lower()
        return await session.scalar(select(User).where(User.email == email_norm))

    async def get(self, session: AsyncSession, user_id: int) -> Optional[User]:
        return await session.get(User, user_id)

    # ---------- writes (no commit; caller decides) ----------
    async def create_with_org(self, session: AsyncSession, email: str, password: str, org_name: str, role: str = "user") -> User:
        """
        Public signup path: creates Organisation + User atomically.
        Role is server-chosen (default 'user').
        """
        email_norm = email.strip().lower()
        if await self.by_email(session, email_norm):
            raise ValueError("email already registered")

        org = Organisation(name=org_name.strip())
        session.add(org)
        await session.flush()  # get org.id

        user = User(
            org_id=org.id,
            email=email_norm,
            hashed_password=hash_password(password),
            role="user" if role not in ALLOWED_ROLES else role,
            is_active=True,
        )
        session.add(user)
        await session.flush()  # get user.id
        return user

    async def create_in_org(self, session: AsyncSession, *, org_id: int, email: str, password: str, role: str = "user") -> User:
        """
        Admin/provisioning path: create a user inside an existing organisation.
        """
        email_norm = email.strip().lower()
        if await self.by_email(session, email_norm):
            raise ValueError("email already registered")

        user = User(
            org_id=org_id,
            email=email_norm,
            hashed_password=hash_password(password),
            role="user" if role not in ALLOWED_ROLES else role,
            is_active=True,
        )
        session.add(user)
        await session.flush()
        return user

    async def set_role(self, session: AsyncSession, user: User, new_role: str) -> User:
        if new_role not in ALLOWED_ROLES:
            raise ValueError(f"invalid role: {new_role}")
        user.role = new_role
        session.add(user)
        await session.flush()
        return user

    async def activate(self, session: AsyncSession, user: User, active: bool = True) -> User:
        user.is_active = active
        session.add(user)
        await session.flush()
        return user

    async def change_password(self, session: AsyncSession, user: User, new_password: str) -> User:
        user.hashed_password = hash_password(new_password)
        session.add(user)
        await session.flush()
        return user
