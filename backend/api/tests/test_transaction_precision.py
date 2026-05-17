"""
Test Transaction monetary precision and decimal handling.

This module ensures that Transaction.amount properly uses Decimal type for
precise monetary calculations, avoiding float precision errors.
"""
import pytest
from decimal import Decimal
from datetime import datetime, timezone

from src.models import Organisation, User, Upload, Transaction
from src.security import hash_password


@pytest.mark.asyncio
async def test_transaction_amount_decimal_precision(async_db_session):
    """Test that Transaction.amount preserves decimal precision."""
    # Create test organization
    org = Organisation(name="Test Transaction Org")
    async_db_session.add(org)
    await async_db_session.flush()
    
    # Create user
    user = User(
        org_id=org.id,
        email="test@example.com",
        hashed_password=hash_password("password123"),
        role="admin"
    )
    async_db_session.add(user)
    await async_db_session.flush()
    
    # Create upload
    upload = Upload(
        org_id=org.id,
        filename="transactions.csv",
        status="done"
    )
    async_db_session.add(upload)
    await async_db_session.flush()
    
    # Create transaction with precise amount
    transaction = Transaction(
        org_id=org.id,
        upload_id=upload.id,
        txn_date=datetime.now(timezone.utc),
        account_code="4000",
        category="Revenue",
        amount=Decimal("1234.5678"),  # Precise to 4 decimal places
        currency="USD",
        description="Test transaction",
        metadata_json={"source": "test"}
    )
    async_db_session.add(transaction)
    await async_db_session.commit()
    
    # Verify precision is preserved
    assert transaction.amount == Decimal("1234.5678")
    assert isinstance(transaction.amount, Decimal)
    
    # Verify we can do precise arithmetic
    total = transaction.amount + Decimal("0.0001")
    assert total == Decimal("1234.5679")


@pytest.mark.asyncio
async def test_transaction_negative_amounts(async_db_session):
    """Test that negative transaction amounts work correctly."""
    # Create test organization
    org = Organisation(name="Test Negative Org")
    async_db_session.add(org)
    await async_db_session.flush()
    
    # Create upload
    upload = Upload(
        org_id=org.id,
        filename="expenses.csv",
        status="done"
    )
    async_db_session.add(upload)
    await async_db_session.flush()
    
    # Create transaction with negative amount (expense)
    transaction = Transaction(
        org_id=org.id,
        upload_id=upload.id,
        txn_date=datetime.now(timezone.utc),
        account_code="5000",
        category="Expense",
        amount=Decimal("-500.25"),
        currency="USD",
        description="Office supplies",
        metadata_json={}
    )
    async_db_session.add(transaction)
    await async_db_session.commit()
    
    assert transaction.amount == Decimal("-500.25")
    assert transaction.amount < 0


@pytest.mark.asyncio
async def test_transaction_arithmetic_accuracy(async_db_session):
    """Test that decimal arithmetic avoids float precision errors."""
    # Create test organization
    org = Organisation(name="Test Arithmetic Org")
    async_db_session.add(org)
    await async_db_session.flush()
    
    # Create upload
    upload = Upload(
        org_id=org.id,
        filename="test.csv",
        status="done"
    )
    async_db_session.add(upload)
    await async_db_session.flush()
    
    # Create multiple transactions
    amounts = [
        Decimal("0.1"),
        Decimal("0.2"),
        Decimal("0.3"),
        Decimal("1.234567"),  # More precision than typical float
    ]
    
    transactions = []
    for i, amt in enumerate(amounts):
        txn = Transaction(
            org_id=org.id,
            upload_id=upload.id,
            txn_date=datetime.now(timezone.utc),
            account_code=f"400{i}",
            category="Test",
            amount=amt,
            currency="USD",
            metadata_json={}
        )
        transactions.append(txn)
        async_db_session.add(txn)
    
    await async_db_session.commit()
    
    # Sum the amounts - with Decimal this should be exact
    total = sum(t.amount for t in transactions)
    expected = sum(amounts)
    
    # This would fail with floats due to precision errors (0.1 + 0.2 != 0.3)
    assert total == expected
    assert total == Decimal("1.834567")


@pytest.mark.asyncio
async def test_transaction_zero_amount(async_db_session):
    """Test that zero amounts are handled correctly."""
    # Create test organization
    org = Organisation(name="Test Zero Org")
    async_db_session.add(org)
    await async_db_session.flush()
    
    # Create upload
    upload = Upload(
        org_id=org.id,
        filename="test.csv",
        status="done"
    )
    async_db_session.add(upload)
    await async_db_session.flush()
    
    # Create transaction with zero amount
    transaction = Transaction(
        org_id=org.id,
        upload_id=upload.id,
        txn_date=datetime.now(timezone.utc),
        account_code="4000",
        category="Test",
        amount=Decimal("0.0000"),
        currency="USD",
        metadata_json={}
    )
    async_db_session.add(transaction)
    await async_db_session.commit()
    
    assert transaction.amount == Decimal("0.0000")
    assert transaction.amount == 0
