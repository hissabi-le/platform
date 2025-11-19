"""
Test inventory unique constraints and unit differentiation.

This module ensures that inventory items can have the same name but different units
(e.g., "Sugar" in kg vs "Sugar" in lbs), and that the unique constraint properly
enforces uniqueness on (org_id, name, unit).
"""
import pytest
from decimal import Decimal
from sqlalchemy.exc import IntegrityError

from src.models import Organisation, InventoryItem, InventoryMovement, Document
from src.database import get_db


@pytest.mark.asyncio
async def test_inventory_item_unique_constraint_with_different_units(async_db_session):
    """Test that items with same name but different units are allowed."""
    # Create test organization
    org = Organisation(name="Test Inventory Org")
    async_db_session.add(org)
    await async_db_session.flush()
    
    # Create "Sugar" in kg
    item1 = InventoryItem(
        org_id=org.id,
        name="Sugar",
        unit="kg",
        sku=None,
        category="Raw Materials"
    )
    async_db_session.add(item1)
    await async_db_session.flush()
    
    # Create "Sugar" in lbs - should NOT violate constraint
    item2 = InventoryItem(
        org_id=org.id,
        name="Sugar",
        unit="lbs",
        sku=None,
        category="Raw Materials"
    )
    async_db_session.add(item2)
    await async_db_session.commit()
    
    # Verify both items exist
    assert item1.id != item2.id
    assert item1.name == item2.name == "Sugar"
    assert item1.unit == "kg"
    assert item2.unit == "lbs"


@pytest.mark.asyncio
async def test_inventory_item_unique_constraint_violation(async_db_session):
    """Test that duplicate (org_id, name, unit) raises IntegrityError."""
    # Create test organization
    org = Organisation(name="Test Constraint Org")
    async_db_session.add(org)
    await async_db_session.flush()
    
    # Create first "Flour" in kg
    item1 = InventoryItem(
        org_id=org.id,
        name="Flour",
        unit="kg",
        category="Raw Materials"
    )
    async_db_session.add(item1)
    await async_db_session.commit()
    
    # Try to create duplicate "Flour" in kg - should fail
    item2 = InventoryItem(
        org_id=org.id,
        name="Flour",
        unit="kg",
        category="Raw Materials"
    )
    async_db_session.add(item2)
    
    with pytest.raises(IntegrityError) as exc_info:
        await async_db_session.commit()
    
    # SQLite just says "UNIQUE constraint failed" without naming the constraint
    assert "unique constraint" in str(exc_info.value).lower()
    assert "inventory_items" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_inventory_movements_with_decimal_precision(async_db_session):
    """Test that inventory movements preserve decimal precision."""
    # Create test organization
    org = Organisation(name="Test Precision Org")
    async_db_session.add(org)
    await async_db_session.flush()
    
    # Create inventory item
    item = InventoryItem(
        org_id=org.id,
        name="Olive Oil",
        unit="liters",
        category="Ingredients"
    )
    async_db_session.add(item)
    await async_db_session.flush()
    
    # Create movement with precise decimal values
    movement = InventoryMovement(
        org_id=org.id,
        item_id=item.id,
        qty_delta=Decimal("15.123456"),  # 6 decimal places
        unit_cost=Decimal("35.5678"),     # 4 decimal places
        memo="Purchase order #123"
    )
    async_db_session.add(movement)
    await async_db_session.commit()
    
    # Verify precision is preserved
    assert movement.qty_delta == Decimal("15.123456")
    assert movement.unit_cost == Decimal("35.5678")


@pytest.mark.asyncio
async def test_inventory_item_cross_org_uniqueness(async_db_session):
    """Test that same item name+unit in different orgs doesn't violate constraint."""
    # Create two organizations
    org1 = Organisation(name="Restaurant A")
    org2 = Organisation(name="Restaurant B")
    async_db_session.add_all([org1, org2])
    await async_db_session.flush()
    
    # Create "Salt" in kg for org1
    item1 = InventoryItem(
        org_id=org1.id,
        name="Salt",
        unit="kg",
        category="Seasonings"
    )
    async_db_session.add(item1)
    
    # Create "Salt" in kg for org2 - should be allowed (different org)
    item2 = InventoryItem(
        org_id=org2.id,
        name="Salt",
        unit="kg",
        category="Seasonings"
    )
    async_db_session.add(item2)
    await async_db_session.commit()
    
    # Both should exist
    assert item1.id != item2.id
    assert item1.org_id != item2.org_id
