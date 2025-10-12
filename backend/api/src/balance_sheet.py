import logging
import math
from typing import Iterable, Mapping

logger = logging.getLogger(__name__)

# ---------------- helpers ----------------

def _iter_rows(data: Iterable[Mapping]):
    """
    Accept either a pandas DataFrame (via .iterrows) or any iterable of mappings.
    """
    if hasattr(data, "iterrows"):
        for _, row in data.iterrows():  # pragma: no cover (only when pandas is installed)
            yield row
    else:
        for row in data:
            yield row

def _is_nan(value: object) -> bool:
    return isinstance(value, float) and math.isnan(value)

def _get_ci(row: Mapping, *names: str, default=None):
    """
    Case-insensitive field fetch: try any of `names` in any case; fall back to default.
    """
    # direct exact match first
    for n in names:
        if n in row:
            return row[n]
    # case-insensitive scan
    lower = {str(k).lower(): k for k in row.keys()}
    for n in names:
        k = lower.get(n.lower())
        if k is not None:
            return row[k]
    return default

# ---------------- classification sets ----------------

ASSET_KEYS = {
    "cash", "receivable", "inventory", "asset", "accumulated",
    "prepaid", "investment", "property", "equipment", "land", "building"
}
LIAB_KEYS = {
    "payable", "debt", "loan", "accrued", "liability", "tax", "bond", "deferred"
}
EQUITY_KEYS = {"equity", "capital", "stock", "retained", "earnings", "dividend"}

# Expanded P&L keywords (mine had broader coverage; keep it)
PL_KEYWORDS = {
    "revenue", "sales", "income", "turnover",
    "cogs", "cost of goods", "cost-of-goods",
    "expense", "operating", "rent", "salary", "salaries", "wage",
    "utilities", "marketing", "advertising", "admin", "depreciation"
}

# ---------------- main ----------------

def generate_balance_sheet(data: Iterable[Mapping]) -> dict:
    """
    Merged implementation:
    - Accepts DataFrame or iterable of mappings
    - Case-insensitive for 'Account'/'Amount' (and allows 'Item' when account missing)
    - Skips NaN and near-zero amounts
    - Uses explicit asset/liability/equity keyword lists; otherwise sign fallback
    - Excludes obvious P&L accounts via PL_KEYWORDS
    - Stores Assets and Liabilities as positive numbers
    - Closes Equity as Assets - Liabilities (Retained Earnings)
    - Returns both lower-case structure (for API) and capitalized 'compat' structure,
      including category totals, Total Liabilities and Equity, and Balanced flag
    """
    assets: dict[str, float] = {}
    liabilities: dict[str, float] = {}
    equity: dict[str, float] = {}

    for row in _iter_rows(data):
        acct_name = _get_ci(row, "Account", "account", "Item", "item", default="")
        acct_name = str(acct_name).strip()
        if not acct_name:
            continue

        amt = _get_ci(row, "Amount", "amount", default=None)
        if amt is None or _is_nan(amt):
            continue
        try:
            amt = float(amt)
        except Exception:
            # not numeric – ignore
            continue
        if abs(amt) < 1e-9:  # suppress near-zero noise
            continue

        name_lower = acct_name.lower()
        # Exclude obvious P&L lines from BS
        if any(key in name_lower for key in PL_KEYWORDS):
            logger.info("Skipping P&L account '%s' in balance sheet generation.", acct_name)
            continue

        # Choose category
        if any(k in name_lower for k in ASSET_KEYS):
            category = "asset"
        elif any(k in name_lower for k in LIAB_KEYS):
            category = "liab"
        elif any(k in name_lower for k in EQUITY_KEYS):
            category = "equity"
        else:
            # sign heuristic fallback
            category = "asset" if amt >= 0 else "liab"

        # Aggregate with positive magnitudes for clarity
        if category == "asset":
            assets[acct_name] = assets.get(acct_name, 0.0) + amt
        elif category == "liab":
            # store as positive number
            liabilities[acct_name] = liabilities.get(acct_name, 0.0) + abs(amt)
        else:
            equity[acct_name] = equity.get(acct_name, 0.0) + amt

    # Compute positive totals
    total_assets = sum(v for v in assets.values() if not _is_nan(v))
    total_liab = sum(v for v in liabilities.values() if not _is_nan(v))
    # Close equity to enforce balance
    closed_equity = total_assets - total_liab
    equity["Retained Earnings"] = equity.get("Retained Earnings", 0.0) + closed_equity
    total_equity = sum(v for v in equity.values() if not _is_nan(v))

    # Balanced flag (|A - (L + E)| < eps)
    balanced = abs(total_assets - (total_liab + total_equity)) < 1e-2

    # Lower-case primary structure (API used this shape before)
    bs = {
        "assets": dict(assets),
        "liabilities": dict(liabilities),
        "equity": dict(equity),
        "totals": {
            "assets": total_assets,
            "liabilities": total_liab,
            "equity": total_equity,
        },
        "balanced": balanced,
    }

    # Capitalized compatibility view (like your original)
    assets_cap = dict(assets)
    liabilities_cap = dict(liabilities)
    equity_cap = dict(equity)
    assets_cap["Total Assets"] = total_assets
    liabilities_cap["Total Liabilities"] = total_liab
    equity_cap["Total Equity"] = total_equity
    compat = {
        "Assets": assets_cap,
        "Liabilities": liabilities_cap,
        "Equity": equity_cap,
        "Total Liabilities and Equity": total_liab + total_equity,
        "Balanced": balanced,
    }

    # Include both views so downstream code/tests can pick their preferred one.
    bs["compat"] = compat
    return bs
