#!/usr/bin/env python3
"""
Seed script to create a test account for Hisabi Personal demo.

Usage:
    SEED_EMAIL=demo@example.com SEED_PASSWORD=changeme \\
        python -m scripts.seed_personal_demo

Both SEED_EMAIL and SEED_PASSWORD are required — there are no defaults.
"""
import asyncio
import os
import random
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import delete, select

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database import async_session
from src.models import (
    Organisation,
    PersonalBudget,
    PersonalEntry,
    Subscription,
    User,
)


SEED_EMAIL = os.environ.get("SEED_EMAIL")
SEED_PASSWORD = os.environ.get("SEED_PASSWORD")

if not SEED_EMAIL or not SEED_PASSWORD:
    sys.stderr.write(
        "error: SEED_EMAIL and SEED_PASSWORD must be set in the environment.\n"
    )
    sys.exit(2)


VENDORS = {
    "groceries": ["Whole Foods", "Trader Joe's", "Costco", "Safeway", "Sprouts"],
    "dining": ["Olive Garden", "Chipotle", "In-N-Out", "Panda Express", "Cheesecake Factory"],
    "delivery": ["DoorDash", "Uber Eats", "Grubhub"],
    "alcohol": ["Total Wine", "BevMo"],
    "nightlife": ["The Blue Bar", "Rooftop Lounge"],
    "fitness": ["Equinox", "Barry's Bootcamp", "SoulCycle", "ClassPass"],
    "wellness": ["Massage Envy", "Float Lab"],
    "fashion": ["Nordstrom", "Zara", "H&M", "Nike"],
    "entertainment": ["AMC Theatres", "Netflix", "Spotify", "Steam"],
    "personal_care": ["Sephora", "Ulta", "Target Beauty"],
    "rent": ["Property Management"],
    "utilities": ["PG&E", "Comcast", "AT&T"],
    "household": ["Home Depot", "IKEA", "Amazon"],
    "subscriptions": ["Adobe", "iCloud", "YouTube Premium", "Notion"],
    "transportation": ["Uber", "Lyft", "Shell", "Chevron", "Parking"],
    "healthcare": ["CVS Pharmacy", "Kaiser", "Walgreens"],
    "education": ["Coursera", "Udemy", "Skillshare"],
    "travel": ["United Airlines", "Marriott", "Airbnb", "Booking.com"],
    "gifts": ["Amazon", "Target", "Best Buy"],
    "other": ["Miscellaneous"],
}

AMOUNT_RANGES = {
    "groceries": (40, 180),
    "dining": (15, 85),
    "delivery": (18, 55),
    "alcohol": (25, 90),
    "nightlife": (30, 120),
    "fitness": (30, 60),
    "wellness": (50, 150),
    "fashion": (40, 200),
    "entertainment": (10, 60),
    "personal_care": (20, 100),
    "rent": (2200, 2200),
    "utilities": (80, 200),
    "household": (30, 150),
    "subscriptions": (10, 25),
    "transportation": (15, 80),
    "healthcare": (20, 100),
    "education": (15, 50),
    "travel": (150, 500),
    "gifts": (30, 100),
    "other": (10, 50),
}

FREQUENCY = {
    "groceries": 8,
    "dining": 10,
    "delivery": 6,
    "alcohol": 2,
    "nightlife": 3,
    "fitness": 8,
    "wellness": 1,
    "fashion": 2,
    "entertainment": 4,
    "personal_care": 2,
    "rent": 1,
    "utilities": 3,
    "household": 3,
    "subscriptions": 4,
    "transportation": 12,
    "healthcare": 1,
    "education": 1,
    "travel": 0,
    "gifts": 1,
    "other": 2,
}


async def create_sample_data() -> None:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.email == SEED_EMAIL))
        user = result.scalar_one_or_none()

        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
        hashed = pwd_context.hash(SEED_PASSWORD)

        if not user:
            org = Organisation(name="Personal Demo Org")
            session.add(org)
            await session.flush()

            sub = Subscription(
                org_id=org.id,
                stripe_subscription_id="sub_demo_personal",
                plan="personal",
                status="active",
            )
            session.add(sub)

            user = User(
                email=SEED_EMAIL,
                hashed_password=hashed,
                role="admin",
                org_id=org.id,
            )
            session.add(user)
            await session.flush()
            print(f"Created user: {SEED_EMAIL}")
        else:
            user.hashed_password = hashed
            session.add(user)
            await session.flush()
            print(f"User exists: {SEED_EMAIL} — password reset")

            await session.execute(
                delete(PersonalEntry).where(PersonalEntry.user_id == user.id)
            )
            await session.execute(
                delete(PersonalBudget).where(PersonalBudget.user_id == user.id)
            )

        user_id = user.id
        today = date.today()
        entries_created = 0

        for days_ago in range(30):
            entry_date = today - timedelta(days=days_ago)

            if entry_date.day == 1 or entry_date.day == 15:
                income = PersonalEntry(
                    user_id=user_id,
                    entry_date=entry_date,
                    entry_type="income",
                    category="salary",
                    amount=Decimal("3250.00"),
                    currency="USD",
                    description="Paycheck",
                    vendor="Employer Inc.",
                    ai_categorized=False,
                )
                session.add(income)
                entries_created += 1

            for category, monthly_freq in FREQUENCY.items():
                daily_prob = monthly_freq / 30.0
                if random.random() < daily_prob:
                    vendors = VENDORS.get(category, ["Unknown"])
                    vendor = random.choice(vendors)
                    min_amt, max_amt = AMOUNT_RANGES.get(category, (10, 50))
                    amount = round(random.uniform(min_amt, max_amt), 2)

                    entry = PersonalEntry(
                        user_id=user_id,
                        entry_date=entry_date,
                        entry_type="expense",
                        category=category,
                        amount=Decimal(str(amount)),
                        currency="USD",
                        description=f"{category.replace('_', ' ').title()} at {vendor}",
                        vendor=vendor,
                        ai_categorized=random.choice([True, False]),
                    )
                    session.add(entry)
                    entries_created += 1

        budgets = [
            ("dining", 400),
            ("groceries", 600),
            ("entertainment", 150),
            ("transportation", 300),
            ("subscriptions", 100),
        ]

        for category, limit in budgets:
            budget = PersonalBudget(
                user_id=user_id,
                category=category,
                monthly_limit=Decimal(str(limit)),
            )
            session.add(budget)

        await session.commit()

        print(f"Created {entries_created} personal entries")
        print(f"Created {len(budgets)} budgets")


if __name__ == "__main__":
    asyncio.run(create_sample_data())
