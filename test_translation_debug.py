"""
Quick debug script to check user's preferred language in database.
Run this to see what's in the database.
"""

import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.user import User


async def check_users():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

        print("=" * 70)
        print("📊 USER LANGUAGE PREFERENCES")
        print("=" * 70)

        for user in users:
            print(f"\nUser: {user.phone_number}")
            print(f"  ID: {user.id}")
            print(f"  Name: {user.name}")
            print(f"  Preferred Language: {user.preferred_language}")
            print(f"  Created: {user.created_at}")

        print("\n" + "=" * 70)
        print(f"Total Users: {len(users)}")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(check_users())
