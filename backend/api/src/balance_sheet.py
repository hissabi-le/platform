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

PNL_REVENUE_KEYS = {"revenue", "sales", "income", "turnover", "receipt"}
PNL_COGS_KEYS = {"cogs", "cost of goods", "cost-of-goods", "inventory cost"}
PNL_EXPENSE_KEYS = {
    "expense", "operating", "rent", "salary", "salaries", "wage", "utilities",
    "marketing", "advertising", "admin", "general", "depreciation", "tax"
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

        if category == "asset":
            assets[acct_name] = assets.get(acct_name, 0.0) + amt
        elif category == "liab":
            liabilities[acct_name] = liabilities.get(acct_name, 0.0) + amt
        else:
            equity[acct_name] = equity.get(acct_name, 0.0) + amt

    total_assets = sum(v for v in assets.values() if not _is_nan(v))
    total_liab_signed = sum(v for v in liabilities.values() if not _is_nan(v))
    total_equity_signed = sum(v for v in equity.values() if not _is_nan(v))

    balance_gap = total_assets + total_liab_signed + total_equity_signed
    balanced = abs(balance_gap) < 1e-2

    # Display-friendly copies (positive magnitudes)
    assets_disp = {name: float(value) for name, value in assets.items()}
    liabs_disp = {name: abs(float(value)) for name, value in liabilities.items()}
    equity_disp = {name: abs(float(value)) for name, value in equity.items()}

    total_liab_display = sum(liabs_disp.values())
    total_equity_display = sum(equity_disp.values())

    # When equity rows are absent, fall back to computed residual (positive magnitude).
    if not equity_disp and not math.isclose(total_assets, 0.0, abs_tol=1e-9):
        residual = max(total_assets - total_liab_display, 0.0)
        if residual:
            equity_disp["Retained Earnings"] = residual
            total_equity_display = residual

    totals_section = {
        "assets": total_assets,
        "liabilities": total_liab_display,
        "equity": total_equity_display,
    }

    # Lower-case primary structure (API used this shape before)
    bs = {
        "assets": dict(assets_disp),
        "liabilities": dict(liabs_disp),
        "equity": dict(equity_disp),
        "totals": totals_section,
        "balanced": balanced,
    }

    # Capitalized compatibility view (like your original)
    assets_cap = dict(assets_disp)
    liabilities_cap = dict(liabs_disp)
    equity_cap = dict(equity_disp)
    assets_cap["Total Assets"] = total_assets
    liabilities_cap["Total Liabilities"] = total_liab_display
    equity_cap["Total Equity"] = total_equity_display
    compat = {
        "Assets": assets_cap,
        "Liabilities": liabilities_cap,
        "Equity": equity_cap,
        "Total Liabilities and Equity": total_liab_display + total_equity_display,
        "Balanced": balanced,
    }

    # Include both views so downstream code/tests can pick their preferred one.
    bs["compat"] = compat
    return bs


def _classify_pnl_bucket(name: str, default: str, category: str | None = None) -> str:
    """
    Heuristic bucket classifier for P&L rows. Prefers explicit category keywords,
    falls back to amount sign based defaults.
    """
    lower = name.lower()
    cat_lower = (category or "").lower()

    def _match(keys: set[str]) -> bool:
        return any(key in lower for key in keys) or any(key in cat_lower for key in keys)

    if _match(PNL_REVENUE_KEYS):
        return "revenue"
    if _match(PNL_COGS_KEYS):
        return "cogs"
    if _match(PNL_EXPENSE_KEYS):
        return "expense"
    return default


def generate_pnl(data: Iterable[Mapping]) -> dict:
    """
    Aggregate a profit & loss structure from transaction-like rows.
    Expected fields include 'Account'/'account', 'Category'/'category', and 'Amount'/'amount'.
    Unknown columns gracefully fall back, keeping this usable with minimal inputs.
    """
    revenue_total = 0.0
    cogs_total = 0.0
    expenses: dict[str, float] = {}

    for row in _iter_rows(data):
        name = _get_ci(row, "Account", "account", "Category", "category", "Description", "description", default="")
        name = str(name).strip()
        if not name:
            continue

        amount = _get_ci(row, "Amount", "amount", default=None)
        if amount is None or _is_nan(amount):
            continue
        try:
            amount_val = float(amount)
        except Exception:
            continue
        if abs(amount_val) < 1e-9:
            continue

        category = _get_ci(row, "Category", "category", default=None)
        default_bucket = "revenue" if amount_val >= 0 else "expense"
        bucket = _classify_pnl_bucket(name, default_bucket, category=str(category) if category else None)

        if bucket == "revenue":
            revenue_total += amount_val
        elif bucket == "cogs":
            cogs_total += abs(amount_val)
        else:
            expenses[name] = expenses.get(name, 0.0) + abs(amount_val)

    gross_profit = revenue_total - cogs_total
    total_expenses = sum(expenses.values())
    net_income = gross_profit - total_expenses

    return {
        "revenue": revenue_total,
        "cogs": cogs_total,
        "gross_profit": gross_profit,
        "expenses": expenses,
        "total_expenses": total_expenses,
        "net_income": net_income,
    }


def compute_roi(pnl: Mapping[str, float]) -> dict:
    """
    Basic ROI helper derived from the generated P&L:
    ROI = Net Income / (COGS + Operating Expenses) when denominator > 0.
    """
    revenue = float(pnl.get("revenue", 0.0) or 0.0)
    cogs = float(pnl.get("cogs", 0.0) or 0.0)
    total_expenses = float(pnl.get("total_expenses", 0.0) or 0.0)
    net_income = float(pnl.get("net_income", revenue - cogs - total_expenses))

    investment = cogs + total_expenses
    roi_value = net_income / investment if investment > 0 else None

    return {
        "net_income": net_income,
        "total_investment": investment,
        "roi": roi_value,
    }
