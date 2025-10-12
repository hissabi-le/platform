from __future__ import annotations
import csv
import re
import logging
from typing import Iterable, Optional

import pandas as pd

logger = logging.getLogger(__name__)


# Canonical header map (case-insensitive) used after loading
_COMMON_MAP = {
    "item": "Item", "product": "Item", "description": "Item", "name": "Item",
    "sku": "SKU", "code": "SKU",
    "qty": "Qty", "quantity": "Qty", "qtty": "Qty", "qte": "Qty",
    "unit": "Unit", "units": "Unit", "uom": "Unit",
    "account": "Account", "acct": "Account",
    "debit": "Debit", "credit": "Credit",
    "amount": "Amount", "total": "Amount", "value": "Amount", "price": "Price", "cost": "Cost",
    "date": "Date", "posting date": "Date", "ts": "Date", "datetime": "Date",
}

_SECTION_WORDS = {"assets", "liabilities", "equity", "income", "expenses", "revenue", "p&l"}

# ---------------- Arabic numerals & separators ----------------
_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def _normalize_text(s: str) -> str:
    # strip currency words/symbols that often appear
    s = s.replace("\u00a0", " ")  # NBSP
    s = s.replace("٬", "")  # Arabic thousands
    s = s.translate(_ARABIC_DIGITS)
    s = s.replace(",", "")
    s = s.replace("LBP", "").replace("ل.ل", "")
    return s


def convert_to_numeric(series: pd.Series) -> pd.Series:
    """Your CR/DR + parentheses negatives, with Arabic digits & cleanup."""
    def _parse(val) -> float | None:
        if pd.isna(val):
            return None
        s = str(val).strip()
        if s == "":
            return None
        low = s.lower()
        sign = 1.0
        # parentheses → negative
        if re.fullmatch(r"\(.*\)", s):
            sign *= -1.0
            s = s.strip("()").strip()
        # trailing CR/DR
        if low.endswith(" cr") or low.endswith("cr"):
            sign *= -1.0
            s = re.sub(r"\s*cr$", "", s, flags=re.IGNORECASE).strip()
        elif low.endswith(" dr") or low.endswith("dr"):
            s = re.sub(r"\s*dr$", "", s, flags=re.IGNORECASE).strip()
        # currency & non-digits
        s = _normalize_text(s)
        s = re.sub(r"[^0-9.\-]", "", s)
        if s in {"", "-", "."}:
            return None
        try:
            return sign * float(s)
        except ValueError:
            return None
    return series.map(_parse)


def determine_header_row_xlsx(file_path: str, max_probe: int = 8) -> int:
    """Heuristically pick header row by minimizing Unnamed columns (your approach)."""
    best_row = 0
    best_score = float("inf")
    for header in range(max_probe):
        try:
            df_test = pd.read_excel(file_path, header=header, dtype=str)
        except Exception as e:  # pragma: no cover
            logger.error("Error reading file with header=%s: %s", header, e)
            break
        unnamed_count = sum(1 for col in df_test.columns if str(col).startswith("Unnamed"))
        if unnamed_count < best_score:
            best_score = unnamed_count
            best_row = header
        if unnamed_count == 0:
            break
    return best_row


def _read_csv(path: str) -> pd.DataFrame:
    # delimiter sniffing; let pandas infer via engine="python"
    try:
        return pd.read_csv(path, sep=None, engine="python", dtype=str, keep_default_na=False, na_values=["", "NaN", "nan"])
    except Exception:
        return pd.read_csv(path, dtype=str, encoding="utf-8-sig", keep_default_na=False, na_values=["", "NaN", "nan"])


def _read_excel(path: str) -> pd.DataFrame:
    header = determine_header_row_xlsx(path)
    df = pd.read_excel(path, header=header, dtype=str)
    return df


def load_table(file_path: str) -> pd.DataFrame:
    """Load CSV/XLSX with robust defaults (strings where possible)."""
    if file_path.lower().endswith(".csv"):
        df = _read_csv(file_path)
    else:
        df = _read_excel(file_path)
    # drop fully empty rows/cols
    df = df.dropna(axis=0, how="all").dropna(axis=1, how="all").copy()
    # normalize whitespace in headers
    df.columns = [re.sub(r"\s+", " ", str(c)).strip() for c in df.columns]
    return df


def _normalize_headers(df: pd.DataFrame) -> pd.DataFrame:
    lower = {c.lower(): c for c in df.columns}
    for k, v in _COMMON_MAP.items():
        if k in lower and v not in df.columns:
            df = df.rename(columns={lower[k]: v})
    return df


def _drop_section_and_total_rows(df: pd.DataFrame, account_col: Optional[str]) -> pd.DataFrame:
    if not account_col or account_col not in df:
        return df
    s = df[account_col].astype(str).str.strip().str.lower()
    # section headers w/out amounts (e.g., "Assets:")
    section_mask = s.str.replace(":", "", regex=False).isin(_SECTION_WORDS)
    # explicit total/subtotal rows
    total_mask = s.str.startswith("total") | s.str.startswith("subtotal")
    df = df[~(section_mask | total_mask)].copy()
    return df


def _coerce_numeric_columns(df: pd.DataFrame, numeric_candidates: list[str]) -> pd.DataFrame:
    for c in numeric_candidates:
        if c in df.columns:
            df[c] = convert_to_numeric(df[c])
    return df


def _derive_amount(df: pd.DataFrame) -> pd.DataFrame:
    cols = {c.lower(): c for c in df.columns}
    if "amount" in cols:
        df[cols["amount"]] = convert_to_numeric(df[cols["amount"]])
        return df
    if "debit" in cols and "credit" in cols:
        debit = convert_to_numeric(df[cols["debit"]]).fillna(0)
        credit = convert_to_numeric(df[cols["credit"]]).fillna(0)
        df = df.assign(Amount=debit - credit)
    return df


def _pick_main_amount_column(df: pd.DataFrame) -> str | None:
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if not numeric_cols:
        return None
    if len(numeric_cols) == 1:
        return numeric_cols[0]
    totals = {c: pd.to_numeric(df[c], errors="coerce").abs().sum() for c in numeric_cols}
    return max(totals, key=totals.get)


def clean_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    General-purpose cleaner for both ledger-like and item-list sheets.
    Returns a DataFrame that *preserves* useful columns for downstream steps,
    while standardizing the following if present: Account, Item, SKU, Qty, Unit,
    Date, Debit, Credit, Amount.
    """
    df = df.dropna(axis=0, how="all").dropna(axis=1, how="all").copy()

    # Normalize headers to canonical names
    df = _normalize_headers(df)

    # Heuristic account & item columns
    account_col = "Account" if "Account" in df.columns else None
    if not account_col:
        for cand in ["Item", "Description", "Name"]:
            if cand in df.columns:
                account_col = cand
                break

    # Drop obvious section/total rows using your heuristics
    df = _drop_section_and_total_rows(df, account_col)

    # If both Debit/Credit exist, compute Amount; else coerce Amount if present
    df = _derive_amount(df)

    # Coerce other numeric columns we care about
    numeric_candidates = [c for c in ["Qty", "Price", "Cost", "Amount"] if c in df.columns]
    df = _coerce_numeric_columns(df, numeric_candidates)

    # If there are multiple numeric columns, pick the main amount (your magnitude rule)
    main_amount = _pick_main_amount_column(df)

    # If we found a main amount column that's not already named Amount, rename
    if main_amount and main_amount != "Amount":
        df = df.rename(columns={main_amount: "Amount"})

    # If we still don't have any numeric column, surface an error like your version
    if "Amount" not in df.columns and not any(pd.api.types.is_numeric_dtype(df[c]) for c in df.columns):
        raise ValueError("No numeric column found in data.")

    # Prefer to expose both views:
    # - For ledger: ensure columns are Account, Amount
    # - For inventory: keep Item/SKU/Qty/Unit if present
    # If no explicit Account but we had an account-like column, rename it to Account
    if account_col and account_col in df.columns and account_col != "Account":
        df = df.rename(columns={account_col: "Account"})

    # Optional tidy: if Item missing but Account exists, create Item alias for inventory LLM
    if "Item" not in df.columns and "Account" in df.columns:
        df = df.assign(Item=df["Account"])

    # Reorder to put canonical columns first (others preserved at the end)
    ordered = [c for c in ["Date","Account","Item","SKU","Qty","Unit","Debit","Credit","Amount"] if c in df.columns]
    return df[ordered + [c for c in df.columns if c not in ordered]]


# Backwards-compatible wrappers (names from your implementation)

def process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Alias to clean_table for compatibility with earlier code/tests."""
    return clean_table(df)


def clean_excel(file_path: str) -> pd.DataFrame:
    """High-level wrapper: detect header row (xlsx) and return a cleaned DataFrame."""
    if not file_path.lower().endswith((".xlsx", ".xlsm", ".xls")):
        raise ValueError("clean_excel expects an Excel file path")
    df = load_table(file_path)
    return clean_table(df)

# Older name some modules imported
clean_transactions = clean_table
