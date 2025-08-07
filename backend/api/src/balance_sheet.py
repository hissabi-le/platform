import logging
import math
from typing import Iterable, Mapping

logger = logging.getLogger(__name__)


def _iter_rows(data: Iterable[Mapping]):
    """Yield row-like mappings from a variety of inputs.

    The original implementation expected a pandas ``DataFrame`` and used
    ``DataFrame.iterrows``.  The tests in this kata run in a minimal
    environment without pandas, so this helper accepts either a DataFrame or
    any iterable of mappings (e.g. ``list`` of ``dict``).
    """

    if hasattr(data, "iterrows"):
        for _, row in data.iterrows():  # pragma: no cover - exercised when pandas installed
            yield row
    else:
        for row in data:
            yield row


def _is_nan(value: object) -> bool:
    """Return True if ``value`` is a NaN float."""

    return isinstance(value, float) and math.isnan(value)


def generate_balance_sheet(df: Iterable[Mapping]):
    """Generate a balance sheet structure from cleaned account rows.

    ``df`` may be a pandas ``DataFrame`` or any iterable of mappings with the
    keys ``"Account"`` and ``"Amount"``.
    """

    assets: dict[str, float] = {}
    liabilities: dict[str, float] = {}
    equity: dict[str, float] = {}

    asset_keys = [
        "cash",
        "receivable",
        "inventory",
        "asset",
        "accumulated",
        "prepaid",
        "investment",
        "property",
        "equipment",
        "land",
        "building",
    ]
    liab_keys = [
        "payable",
        "debt",
        "loan",
        "accrued",
        "liability",
        "tax",
        "bond",
        "deferred",
    ]
    equity_keys = ["equity", "capital", "stock", "retained", "earnings", "dividend"]

    for row in _iter_rows(df):
        acct_name = str(row["Account"]).strip()
        amt = row["Amount"]
        if amt is None or _is_nan(amt):
            continue  # skip missing amounts
        if isinstance(amt, (int, float)) and abs(amt) < 1e-9:
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
            if (
                "expense" in name_lower
                or "revenue" in name_lower
                or "income" in name_lower
            ):
                logger.info(
                    "Skipping P&L account '%s' in balance sheet generation.", acct_name
                )
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
    return {
        "Assets": assets,
        "Liabilities": liabilities,
        "Equity": equity,
        "Total Liabilities and Equity": total_liab_and_equity,
        "Balanced": balanced,
    }
