import pandas as pd
from backend.api.src.excel_cleaner import convert_to_numeric, process_dataframe
from backend.api.src.balance_sheet import generate_balance_sheet

def test_convert_to_numeric():
    # series with various formats to convert
    s = pd.Series(["$1,000.00", "500", "(250)", "73 Cr", "27 dr", "N/A"])
    result = convert_to_numeric(s)
    # expected results: 1000.00, 500.0, -250.0, -73.0, 27.0, NaN
    expected = [1000.0, 500.0, -250.0, -73.0, 27.0, None]
    # compare each, allowing NaN for the last
    assert result.iloc[0] == expected[0]
    assert result.iloc[1] == expected[1]
    assert result.iloc[2] == expected[2]
    assert result.iloc[3] == expected[3]
    assert result.iloc[4] == expected[4]
    assert pd.isna(result.iloc[5]), "Expected NaN for non-numeric input"

def test_balance_sheet_generation_balanced():
    # Create a df representing cleaned trial balance that balances.
    data = {
        "Account": ["Cash", "Accounts Receivable", "Accounts Payable", "Common Stock"],
        "Amount": [1000, 500, -300, -1200] 
        # This is balanced: assets 1500, liabilities -300, equity -1200 (assets = 1500, liab+equity = -1500)
    }
    df = pd.DataFrame(data)
    result = generate_balance_sheet(df)
    # check totals
    assert result["Assets"]["Total Assets"] == 1500
    assert result["Liabilities"]["Total Liabilities"] == -300
    assert result["Equity"]["Total Equity"] == -1200
    # Liabilities + Equity total should be -1500
    assert result["Total Liabilities and Equity"] == -1500
    # balanced flag should be true
    assert result["Balanced"] is True

def test_balance_sheet_generation_unbalanced():
    # Create data that doesn't balance (e.g., missing an equity entry)
    data = {
        "Account": ["Cash", "Loan Payable"],
        "Amount": [1000, -600] 
        # Here assets = 1000, liabilities = -600, equity = 0 (not balanced, net 400 missing)
    }
    df = pd.DataFrame(data)
    result = generate_balance_sheet(df)
    # It should mark Balanced as False
    assert result["Balanced"] is False
    # The difference of assets and (liabilities+equity) should be reflected in imbalance
    total_assets = result["Assets"]["Total Assets"]
    total_liab_equity = result["Total Liabilities and Equity"]
    assert abs(total_assets + total_liab_equity) > 1e-2  # not close to zero
