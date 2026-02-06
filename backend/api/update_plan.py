#!/usr/bin/env python3
"""Quick script to update user plan to 'personal' for testing."""
import asyncio
from sqlalchemy import select, update
from src.database import async_session
from src.models import User

async def main():
    async with async_session() as session:
        # Update all users to have 'personal' plan
        stmt = update(User).values(plan="personal")
        await session.execute(stmt)
        await session.commit()
        
        # Verify
        result = await session.execute(select(User))
        users = result.scalars().all()
        for user in users:
            print(f"User {user.email}: plan = {user.plan}")

if __name__ == "__main__":
    asyncio.run(main())
