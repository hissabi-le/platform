import datetime
from decimal import Decimal

import pytest

from fastapi.testclient import TestClient

from src.main import app


client = TestClient(app)


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register_user(suffix: str = "") -> tuple[str, dict]:
    email = f"journal{suffix}@test.com"
    payload = {"email": email, "password": "secret12345", "org_name": f"Journal Org {suffix or 'A'}"}
    resp = client.post("/auth/register", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    token = body["access_token"]
    return token, body["user"]


@pytest.mark.parametrize("commit_flag", [False, True])
def test_journal_day_flow(commit_flag):
    suffix = "preview" if not commit_flag else "commit"
    token, user = _register_user(suffix)
    headers = _auth_headers(token)

    # configure baseline investment for roi
    resp = client.put(
        "/settings/org",
        headers=headers,
        json={"total_initial_investment": "1000", "starting_cash_balance": "200", "current_assets_value": "500"},
    )
    assert resp.status_code == 200

    journal_text = "\n".join(
        [
            "sold 5 coffees for $25",
            "bought milk 3 kg for $15",
            "بعت 2 عصير 200000 ل.ل",
            "acheté sucre 10$",
            "paid rent $400",
        ]
    )

    resp = client.post(
        "/journal/day",
        headers=headers,
        json={"raw_text": journal_text, "date": "2025-10-27", "commit": commit_flag},
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["journal_day"]["parse_status"] in {"parsed", "needs_review"}
    totals = body["totals"]
    assert float(totals["revenue"]) > 0
    assert float(totals["cost"]) >= 400

    # preview should not persist; commit should persist and be retrievable
    if commit_flag:
        day_id = body["journal_day"]["id"]
        assert day_id is not None
        resp_get = client.get("/journal/day", headers=headers, params={"date_str": "2025-10-27"})
        assert resp_get.status_code == 200
        fetched = resp_get.json()
        assert fetched["journal_day"]["id"] == day_id
        resp_dup = client.post(
            "/journal/day",
            headers=headers,
            json={"raw_text": journal_text, "date": "2025-10-27"},
        )
        assert resp_dup.status_code == 200
        assert resp_dup.json()["journal_day"]["id"] == day_id
    else:
        # ensure preview meta does not include id
        assert body["journal_day"]["id"] is None


def test_journal_resolution_updates_inventory():
    token, user = _register_user("resolve")
    headers = _auth_headers(token)

    # baseline config
    resp = client.put(
        "/settings/org",
        headers=headers,
        json={"total_initial_investment": "2000"},
    )
    assert resp.status_code == 200

    journal_text = "\n".join(
        [
            "sold 10 sandwiches for $50",
            "bought chicken 5 kg for $40",
            "paid electricity $60",
        ]
    )
    resp = client.post(
        "/journal/day",
        headers=headers,
        json={"raw_text": journal_text, "date": "2025-08-15"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    day_id = payload["journal_day"]["id"]
    assert day_id is not None

    purchase_entry = next(entry for entry in payload["entries"] if entry["entry_type"] == "inventory_purchase")
    resolve_payload = {
        "resolutions": [
            {
                "entry_id": purchase_entry["id"],
                "treat_as_inventory": True,
                "quantity": "5",
                "unit": "kg",
                "unit_cost": "8",
                "category": "Ingredients",
            }
        ]
    }

    resp = client.patch(f"/journal/day/{day_id}/resolve", headers=headers, json=resolve_payload)
    assert resp.status_code == 200
    resolved = resp.json()
    assert resolved["journal_day"]["parse_status"] == "parsed"
    totals = resolved["totals"]
    assert float(totals["revenue"]) == 50.0
    # cost should reflect electricity only because inventory is capitalised
    assert float(totals["cost"]) == 60.0
    assert totals["roi"] is not None


def test_settings_roundtrip():
    token, _ = _register_user("settings")
    headers = _auth_headers(token)

    resp = client.get("/settings/org", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(data["total_initial_investment"]) == Decimal("0")

    resp = client.put(
        "/settings/org",
        headers=headers,
        json={"total_initial_investment": "1500.50", "default_currency": "USD"},
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert Decimal(updated["total_initial_investment"]) == Decimal("1500.50")


def test_journal_preview_does_not_persist():
    token, user = _register_user("preview-only")
    headers = _auth_headers(token)

    preview_text = "sold 2 juices for $10\nacheté farine 5$\npaid utilities $5"
    resp = client.post(
        "/journal/day",
        headers=headers,
        json={"raw_text": preview_text, "date": "2025-11-01", "commit": False},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["journal_day"]["id"] is None
    assert payload["journal_day"]["parse_status"] in {"parsed", "needs_review"}
    if payload["clarifications"]:
        assert payload["journal_day"]["parse_status"] == "needs_review"

    resp_get = client.get("/journal/day", headers=headers, params={"date_str": "2025-11-01"})
    assert resp_get.status_code == 404


def test_journal_roi_guard_zero_investment():
    token, _ = _register_user("roi-zero")
    headers = _auth_headers(token)

    # explicitly set investment to zero
    resp = client.put(
        "/settings/org",
        headers=headers,
        json={"total_initial_investment": "0", "starting_cash_balance": "0", "current_assets_value": "0"},
    )
    assert resp.status_code == 200

    journal_text = "sold 5 pizzas for $50\npaid rent $30"
    resp = client.post(
        "/journal/day",
        headers=headers,
        json={"raw_text": journal_text, "date": "2025-11-05"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["totals"]["roi"] is None
