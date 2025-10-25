import pytest

try:  # pragma: no cover - optional dependency
    import pandas as pd  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - handled in tests
    pd = None

from src.balance_sheet import generate_balance_sheet, generate_pnl, compute_roi
if pd:
    from src.excel_cleaner import convert_to_numeric


@pytest.mark.skipif(pd is None, reason="pandas is not installed")
def test_convert_to_numeric():
    s = pd.Series(["$1,000.00", "500", "(250)", "73 Cr", "27 dr", "N/A"])
    result = convert_to_numeric(s)
    expected = [1000.0, 500.0, -250.0, -73.0, 27.0, float("nan")]
    assert result.iloc[0] == expected[0]
    assert result.iloc[1] == expected[1]
    assert result.iloc[2] == expected[2]
    assert result.iloc[3] == expected[3]
    assert result.iloc[4] == expected[4]
    assert pd.isna(result.iloc[5])


def test_balance_sheet_generation_balanced():
    data = [
        {"Account": "Cash", "Amount": 1000},
        {"Account": "Accounts Receivable", "Amount": 500},
        {"Account": "Accounts Payable", "Amount": -300},
        {"Account": "Common Stock", "Amount": -1200},
    ]
    result = generate_balance_sheet(data)
    compat = result["compat"]
    assert compat["Assets"]["Total Assets"] == 1500
    assert compat["Liabilities"]["Total Liabilities"] == 300
    assert compat["Equity"]["Total Equity"] == 1500
    assert compat["Total Liabilities and Equity"] == 1500
    assert compat["Balanced"] is True


def test_balance_sheet_generation_unbalanced():
    data = [
        {"Account": "Cash", "Amount": 1000},
        {"Account": "Loan Payable", "Amount": -600},
    ]
    result = generate_balance_sheet(data)
    assert result["balanced"] is False
    total_assets = result["totals"]["assets"]
    total_liab_equity = result["totals"]["liabilities"] + result["totals"]["equity"]
    assert abs(total_assets - total_liab_equity) > 1e-2


def test_balance_sheet_zero_and_missing():
    data = [
        {"Account": "Cash", "Amount": 0},  # zero amount ignored
        {"Account": "Inventory", "Amount": None},  # missing amount ignored
        {"Account": "Loan Payable", "Amount": -100},
    ]
    result = generate_balance_sheet(data)
    # Only the loan should remain
    assert "Cash" not in result["assets"]
    assert result["liabilities"]["Loan Payable"] == 100


def test_generate_pnl_and_roi():
    rows = [
        {"Account": "Sales Revenue", "Amount": 1000},
        {"Account": "Cost of Goods Sold", "Amount": -400},
        {"Account": "Rent Expense", "Amount": -200},
    ]
    pnl = generate_pnl(rows)
    assert pnl["revenue"] == 1000
    assert pnl["cogs"] == 400
    assert pnl["total_expenses"] == 200
    assert pytest.approx(pnl["net_income"]) == 400

    roi = compute_roi(pnl)
    assert roi["total_investment"] == 600
    assert pytest.approx(roi["roi"]) == pytest.approx(400 / 600)
