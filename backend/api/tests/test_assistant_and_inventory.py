import asyncio
from decimal import Decimal

import pytest

from src.assistant import OpenAIClient
from src.database import async_session
from src.repositories.inventory import InventoryRepo


def test_assistant_heuristic_parse_multilingual():
    client = OpenAIClient(api_key=None)
    lines = [
        "sold 3 sandwiches for $18",
        "acheté lait 6$",
        "استعملت 1 كغ سكر",
    ]
    result = client.parse_journal_lines(lines)
    assert result["language"] in {"en", "fr", "ar"}
    entries = result["entries"]
    assert len(entries) == 3
    assert any(entry["entry_type"] == "revenue" for entry in entries)
    assert any(entry["entry_type"] in {"inventory_purchase", "cost"} for entry in entries)
    amounts = {entry["entry_type"]: entry["total"] for entry in entries}
    assert Decimal(str(amounts.get("revenue", 0))) == Decimal("18")


@pytest.mark.asyncio
async def test_inventory_weighted_average_cost():
    repo = InventoryRepo()
    async with async_session() as session:
        item = await repo.upsert_item(session, org_id=1, name="flour", unit="kg")
        await repo.add_movement(
            session,
            org_id=1,
            item_id=item.id,
            qty_delta=10,
            unit_cost=2.0,
            memo="initial purchase",
            ref_document_id=None,
        )
        await repo.add_movement(
            session,
            org_id=1,
            item_id=item.id,
            qty_delta=5,
            unit_cost=4.0,
            memo="second purchase",
            ref_document_id=None,
        )
        await session.commit()

        wac = await repo.weighted_average_cost(session, org_id=1, item_id=item.id)
        assert wac is not None
        assert wac.quantize(Decimal("0.0001")) == Decimal("2.6667")

        # consume some inventory and recompute
        await repo.add_movement(
            session,
            org_id=1,
            item_id=item.id,
            qty_delta=-3,
            unit_cost=2.6667,
            memo="usage",
            ref_document_id=None,
        )
        await session.commit()
        wac_after = await repo.weighted_average_cost(session, org_id=1, item_id=item.id)
        assert wac_after is not None
        assert wac_after.quantize(Decimal("0.0001")) == Decimal("2.6667")
