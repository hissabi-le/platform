import logging
logger = logging.getLogger(__name__)

def generate_balance_sheet(df):
    """
    Generate a balance sheet structure from a cleaned DataFrame of accounts and amounts.
    Returns a dictionary with Assets, Liabilities, Equity sections and totals.
    """
    assets = {}
    liabilities = {}
    equity = {}
    asset_keys = ["cash", "receivable", "inventory", "asset", "accumulated", "prepaid",
                  "investment", "property", "equipment", "land", "building"]
    liab_keys = ["payable", "debt", "loan", "accrued", "liability", "tax", "bond", "deferred"]
    equity_keys = ["equity", "capital", "stock", "retained", "earnings", "dividend"]
    
    for _, row in df.iterrows():
        acct_name = str(row["Account"]).strip()
        amt = row["Amount"]
        if amt is None or (isinstance(amt, float) and pd.isna(amt)):
            continue  # skip missing amounts
        if abs(amt) < 1e-9:
            continue  # skip zero-valued accounts to avoid clutter (optional)
        name_lower = acct_name.lower()
        # Determine category
        if any(key in name_lower for key in asset_keys):
            category = "Assets"
        elif any(key in name_lower for key in liab_keys):
            category = "Liabilities"
        elif any(key in name_lower for key in equity_keys):
            category = "Equity"
        else:
            # use sign heuristic if no keyword matched
            category = "Assets" if amt >= 0 else "Liabilities"
            # ignore obvious non-balance sheet accounts
            if "expense" in name_lower or "revenue" in name_lower or "income" in name_lower:
                logger.info(f"Skipping P&L account '{acct_name}' in balance sheet generation.")
                continue
        # add to the appropriate category dictionary
        if category == "Assets":
            assets[acct_name] = assets.get(acct_name, 0) + amt
        elif category == "Liabilities":
            liabilities[acct_name] = liabilities.get(acct_name, 0) + amt
        elif category == "Equity":
            equity[acct_name] = equity.get(acct_name, 0) + amt

    # compute totals for each category
    total_assets = sum(assets.values())
    total_liabilities = sum(liabilities.values())
    total_equity = sum(equity.values())
    total_liab_and_equity = total_liabilities + total_equity

    # add totals into the dictionaries
    assets["Total Assets"] = total_assets
    liabilities["Total Liabilities"] = total_liabilities
    equity["Total Equity"] = total_equity

    # check if balanced (Assets = Liabilities + Equity). Using sum of all as zero test:
    balanced = abs(total_assets + total_liabilities + total_equity) < 1e-2

    # build the final result structure
    result = {
        "Assets": assets,
        "Liabilities": liabilities,
        "Equity": equity,
        "Total Liabilities and Equity": total_liab_and_equity,
        "Balanced": balanced
    }
    return result
