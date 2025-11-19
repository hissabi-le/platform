# Inventory Item Unit Differentiation

## Overview

The Hissabi platform's inventory system allows organizations to track the same item with different units of measurement. This is essential for businesses that may purchase, store, or sell items in different units.

## Design

### Unique Constraint

Inventory items are uniquely identified by the combination of:
- `org_id` (Organization ID)
- `name` (Item name)  
- `unit` (Unit of measurement)

This is enforced by the database constraint `uq_item_name_unit_org`.

### Example Use Cases

#### Different Units for Same Item

An organization can have:
- **Sugar** measured in `kg` (kilograms)
- **Sugar** measured in `lbs` (pounds)
- **Sugar** measured in `bags`

Each would be a separate inventory item with its own tracking, movements, and cost calculations.

#### Cross-Organization Independence

Different organizations can have items with the same name and unit without conflicts. For example:
- **Restaurant A** can have "Flour" in `kg`
- **Restaurant B** can also have "Flour" in `kg`

These are completely separate items tracked independently.

## Database Schema

```sql
CREATE TABLE inventory_items (
    id INTEGER PRIMARY KEY,
    org_id INTEGER NOT NULL REFERENCES organisations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    unit VARCHAR(32) NOT NULL DEFAULT 'unit',
    sku VARCHAR(64),
    category VARCHAR(64),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    CONSTRAINT uq_item_name_unit_org UNIQUE (org_id, name, unit)
);

CREATE INDEX ix_item_org_name ON inventory_items (org_id, name);
```

## API Usage

### Creating Items with Different Units

```python
from src.models import InventoryItem

# Create sugar in kilograms
sugar_kg = InventoryItem(
    org_id=1,
    name="Sugar",
    unit="kg",
    category="Raw Materials"
)

# Create sugar in pounds (separate item)
sugar_lbs = InventoryItem(
    org_id=1,
    name="Sugar",
    unit="lbs",
    category="Raw Materials"
)
```

### Inventory Movements

Each item tracks its movements independently:

```python
from src.models import InventoryMovement
from decimal import Decimal

# Purchase 50 kg of sugar
movement_kg = InventoryMovement(
    org_id=1,
    item_id=sugar_kg.id,
    qty_delta=Decimal("50.0"),
    unit_cost=Decimal("2.50"),
    memo="Purchase order #123"
)

# Purchase 100 lbs of sugar (different item)
movement_lbs = InventoryMovement(
    org_id=1,
    item_id=sugar_lbs.id,
    qty_delta=Decimal("100.0"),
    unit_cost=Decimal("1.20"),
    memo="Purchase order #124"
)
```

## Supported Units

The `unit` field is flexible and accepts any string up to 32 characters. Common units include:

### Weight
- `kg` - kilograms
- `g` - grams
- `lbs` - pounds
- `oz` - ounces

### Volume
- `l` - liters
- `ml` - milliliters
- `gal` - gallons
- `qt` - quarts

### Count
- `unit` - individual units (default)
- `piece` - pieces
- `dozen` - dozens
- `box` - boxes
- `case` - cases
- `pallet` - pallets

### Custom Units
Organizations can define their own units as needed, such as:
- `bag` - bags
- `container` - containers
- `batch` - batches

## Important Notes

### Unit Conversion

The system **does not** automatically convert between units. If you have:
- "Sugar" in `kg` with 50 kg on hand
- "Sugar" in `lbs` with 100 lbs on hand

These are tracked separately. Unit conversion must be handled at the application level if needed.

### Precision

All quantity fields use `Decimal` type with 6 decimal places (`Numeric(18, 6)`) to ensure precision:

```python
# Precise quantities are preserved
qty = Decimal("15.123456")  # 15.123456 kg exactly
```

### Best Practices

1. **Standardize Units**: Within an organization, try to standardize on specific units for specific item types
2. **SKU Differentiation**: Use different SKUs for the same item in different units if your business workflow requires it
3. **Clear Naming**: Consider including the unit in the item name for clarity (e.g., "Sugar (Bulk - kg)" vs "Sugar (Retail - lbs)")
4. **Document Conversions**: If you need to convert between units, document the conversion factors in your application code or organization settings

## Testing

The test suite includes comprehensive tests for unit differentiation:

```bash
pytest tests/test_inventory_constraints.py -v
```

Key test cases:
- Same item name with different units is allowed
- Duplicate (org_id, name, unit) is rejected
- Cross-organization items don't conflict
- Decimal precision is preserved in movements

## Migration History

- **Migration 0003_align_models_after_sprint**: Introduced inventory items and movements with the `uq_item_name_unit_org` constraint

## Related Models

- `InventoryItem`: The inventory item definition
- `InventoryMovement`: Tracks quantity changes for items
- `Document`: Can reference movements via `ref_document_id`
