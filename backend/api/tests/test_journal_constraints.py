"""
Test Journal constraints and enum validations.

This module ensures that JournalDay and JournalEntry properly enforce
check constraints on parse_status and entry_type fields.
"""
import pytest
from decimal import Decimal
from datetime import date, datetime
from sqlalchemy.exc import IntegrityError

from src.models import (
    Organisation,
    User,
    JournalDay,
    JournalEntry,
    JournalParseStatus,
    JournalEntryType,
)
from src.security import hash_password


@pytest.mark.asyncio
async def test_journal_day_valid_parse_statuses(async_db_session):
    """Test that valid parse statuses are accepted."""
    # Create test organization and user
    org = Organisation(name="Test Journal Org")
    async_db_session.add(org)
    await async_db_session.flush()
    
    user = User(
        org_id=org.id,
        email="journal@example.com",
        hashed_password=hash_password("password123"),
        role="admin"
    )
    async_db_session.add(user)
    await async_db_session.flush()
    
    # Test all valid statuses
    valid_statuses = ["pending", "parsed", "needs_review", "error"]
    
    for status in valid_statuses:
        journal_day = JournalDay(
            org_id=org.id,
            user_id=user.id,
            journal_date=date.today(),
            raw_text=f"Test journal entry for {status}",
            parse_status=status,
            hash_key=f"hash_{status}",
            total_revenue=Decimal("100.00"),
            total_cost=Decimal("50.00"),
            net_profit=Decimal("50.00"),
        )
        async_db_session.add(journal_day)
        await async_db_session.flush()
        
        assert journal_day.parse_status == status
        
        # Rollback for next iteration to avoid unique constraints
        await async_db_session.rollback()
        await async_db_session.close()
        # Recreate session for next iteration
        from src.database import async_session as create_session
        async_db_session._proxied = (await create_session().__aenter__())


@pytest.mark.asyncio
async def test_journal_entry_valid_entry_types(async_db_session):
    """Test that valid entry types are accepted."""
    # Create test organization
    org = Organisation(name="Test Entry Type Org")
    async_db_session.add(org)
    await async_db_session.flush()
    
    # Create journal day
    journal_day = JournalDay(
        org_id=org.id,
        journal_date=date.today(),
        raw_text="Test journal",
        parse_status="parsed",
        hash_key="test_hash_123",
        total_revenue=Decimal("0"),
        total_cost=Decimal("0"),
        net_profit=Decimal("0"),
    )
    async_db_session.add(journal_day)
    await async_db_session.flush()
    
    # Test all valid entry types
    valid_types = ["revenue", "cost", "inventory_purchase", "inventory_use", "transfer"]
    
    for i, entry_type in enumerate(valid_types):
        entry = JournalEntry(
            org_id=org.id,
            journal_day_id=journal_day.id,
            entry_type=entry_type,
            total=Decimal("10.00"),
            item_name=f"Test item {i}",
        )
        async_db_session.add(entry)
        await async_db_session.flush()
        
        assert entry.entry_type == entry_type
    
    await async_db_session.commit()


@pytest.mark.asyncio
async def test_journal_day_unique_org_date_constraint(async_db_session):
    """Test that org cannot have duplicate journal entries for same date."""
    # Create test organization
    org = Organisation(name="Test Unique Date Org")
    async_db_session.add(org)
    await async_db_session.flush()
    
    # Create first journal day
    journal_day1 = JournalDay(
        org_id=org.id,
        journal_date=date(2025, 1, 15),
        raw_text="First entry",
        parse_status="parsed",
        hash_key="hash_001",
        total_revenue=Decimal("100"),
        total_cost=Decimal("50"),
        net_profit=Decimal("50"),
    )
    async_db_session.add(journal_day1)
    await async_db_session.commit()
    
    # Try to create duplicate for same date
    journal_day2 = JournalDay(
        org_id=org.id,
        journal_date=date(2025, 1, 15),  # Same date!
        raw_text="Second entry",
        parse_status="parsed",
        hash_key="hash_002",
        total_revenue=Decimal("200"),
        total_cost=Decimal("100"),
        net_profit=Decimal("100"),
    )
    async_db_session.add(journal_day2)
    
    with pytest.raises(IntegrityError) as exc_info:
        await async_db_session.commit()
    
    # SQLite says "UNIQUE constraint failed: journal_days.org_id, journal_days.journal_date"
    assert "unique constraint" in str(exc_info.value).lower()
    assert "journal_days" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_journal_entry_monetary_precision(async_db_session):
    """Test that journal entries preserve decimal precision for monetary values."""
    # Create test organization
    org = Organisation(name="Test Precision Org")
    async_db_session.add(org)
    await async_db_session.flush()
    
    # Create journal day
    journal_day = JournalDay(
        org_id=org.id,
        journal_date=date.today(),
        raw_text="Precision test",
        parse_status="parsed",
        hash_key="precision_hash",
        total_revenue=Decimal("1234.5678"),
        total_cost=Decimal("567.8901"),
        net_profit=Decimal("666.6777"),
    )
    async_db_session.add(journal_day)
    await async_db_session.flush()
    
    # Create entry with precise values
    entry = JournalEntry(
        org_id=org.id,
        journal_day_id=journal_day.id,
        entry_type="revenue",
        item_name="Precision Item",
        quantity=Decimal("15.123456"),  # 6 decimal places
        unit="kg",
        unit_cost=Decimal("82.3456"),   # 4 decimal places
        total=Decimal("1234.5678"),
        vat_percent=Decimal("15.00"),
    )
    async_db_session.add(entry)
    await async_db_session.commit()
    
    # Verify precision
    assert entry.quantity == Decimal("15.123456")
    assert entry.unit_cost == Decimal("82.3456")
    assert entry.total == Decimal("1234.5678")
    assert entry.vat_percent == Decimal("15.00")


@pytest.mark.asyncio
async def test_journal_entry_clarification_workflow(async_db_session):
    """Test the clarification workflow for ambiguous entries."""
    # Create test organization
    org = Organisation(name="Test Clarification Org")
    async_db_session.add(org)
    await async_db_session.flush()
    
    # Create journal day
    journal_day = JournalDay(
        org_id=org.id,
        journal_date=date.today(),
        raw_text="Bought stuff",
        parse_status="needs_review",
        hash_key="clarification_hash",
        total_revenue=Decimal("0"),
        total_cost=Decimal("0"),
        net_profit=Decimal("0"),
        clarification_count=1,
    )
    async_db_session.add(journal_day)
    await async_db_session.flush()
    
    # Create ambiguous entry requiring clarification
    entry = JournalEntry(
        org_id=org.id,
        journal_day_id=journal_day.id,
        entry_type="cost",
        item_name="Stuff",
        total=Decimal("50.00"),
        ambiguous=True,
        clarification_question="Is this inventory or expense?",
        resolved=False,
    )
    async_db_session.add(entry)
    await async_db_session.commit()
    
    assert entry.ambiguous is True
    assert entry.resolved is False
    assert entry.clarification_question is not None
