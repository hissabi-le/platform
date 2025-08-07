import pandas as pd
import numpy as np
import logging
import re

logger = logging.getLogger(__name__)

def determine_header_row(file_path):
    """
    Heuristically find which row in the Excel file is the header.
    Tries the first few rows and picks the one with fewest 'Unnamed' columns.
    """
    best_row = 0
    best_score = float('inf')
    for header in range(5):
        try:
            df_test = pd.read_excel(file_path, header=header)
        except Exception as e:
            logger.error(f"Error reading file with header={header}: {e}")
            break
        # count unnamed columns as a proxy for bad header alignment
        unnamed_count = sum([1 for col in df_test.columns if str(col).startswith("Unnamed")])
        if unnamed_count < best_score:
            best_score = unnamed_count
            best_row = header
        if unnamed_count == 0:
            break  # header found
    return best_row

def convert_to_numeric(series):
    """
    Convert a pandas Series of financial strings to numeric values (floats).
    Removes currency symbols, commas, parentheses, and CR/DR notations.

    in: pd.series of raw string data from the excel
    out: pd.series(float) extracted numeric data
    """
    def _parse(val) -> float:
        if pd.isna(val):
            return np.nan
        s = str(val).strip()
        low = s.lower()
        # treat common “null”s as NaN
        if low in ("", "na", "n/a", "-", "--"):
            return np.nan

        sign = 1.0

        # parentheses → negative
        if re.match(r"^\(.*\)$", s):
            sign *= -1.0
            s = s.strip("()").strip()

        # trailing credit/debit markers
        if low.endswith(" cr"):
            sign *= -1.0
            s = s[: -3].strip()
        elif low.endswith("cr"):
            sign *= -1.0
            s = s[: -2].strip()
        elif low.endswith(" dr"):
            # explicit “dr” is positive so just strip
            s = s[: -3].strip()
        elif low.endswith("dr"):
            s = s[: -2].strip()

        # drop commas, currency symbols, and any non digit/dot/minus
        s = s.replace(",", "")
        # remove anything that isn't digit, dot, or minus
        s = re.sub(r"[^0-9\.\-]", "", s)

        try:
            num = float(s)
        except ValueError:
            return np.nan

        return sign * num

    return series.map(_parse)


def process_dataframe(df):
    """
    Clean up a DataFrame that was read from Excel (after header aligned).
    Drops blank rows/cols, removes totals and section labels, and normalizes data.
    Returns a DataFrame with columns 'Account' and 'Amount'.
    """
    # drop empty rows and columns
    df = df.dropna(how='all', axis=0).copy()
    df = df.dropna(how='all', axis=1)
    # Drop account code/number columns if present (not needed for analysis)
    for col in list(df.columns):
        col_lower = str(col).lower()
        if 'account' in col_lower and ('code' in col_lower or 'number' in col_lower):
            df.drop(columns=[col], inplace=True)
    # Identify the likely account name column as the first non-numeric column
    account_col = None
    for col in df.columns:
        if df[col].dtype == object:
            account_col = col
            break
    # remove total rows (any account cell starting with "Total")
    if account_col:
        mask_total = df[account_col].astype(str).str.strip().str.lower().str.startswith('total')
        df = df[~mask_total].copy()
    # combine debit and credit columns into one amount if they exist
    if 'Debit' in df.columns and 'Credit' in df.columns:
        df['Amount'] = df['Debit'].fillna(0) - df['Credit'].fillna(0)
        df.drop(columns=['Debit', 'Credit'], inplace=True)
    # convert object columns that are numeric data to actual numbers
    for col in df.columns:
        if df[col].dtype == object and col != account_col:
            df[col] = convert_to_numeric(df[col])
    # Determine main numeric column (there might be multiple numeric columns if extras were present)
    numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
    if not numeric_cols:
        raise ValueError("No numeric column found in Excel data.")
    main_amount_col = numeric_cols[0]
    if len(numeric_cols) > 1:
        # pick the numeric column with the largest total magnitude as the main amount column
        totals = {col: df[col].abs().sum() for col in numeric_cols}
        main_amount_col = max(totals, key=totals.get)
    # drop rows where the main amount is NaN (non parsable entries)
    df = df[~df[main_amount_col].isna()].copy()
    # Drop section header rows  if they have no amount
    if account_col:
        section_mask = df[account_col].astype(str).str.strip().str.lower().isin(['assets', 'liabilities', 'equity', 'assets:', 'liabilities:', 'equity:']) 
        section_mask &= df[main_amount_col].isna()
        df = df[~section_mask].copy()
    # Drop any remaining numeric columns that are not the main amount (we only need one amount column)
    for col in numeric_cols:
        if col != main_amount_col:
            df.drop(columns=[col], inplace=True)
    # drop any extra text columns besides the account column
    for col in list(df.columns):
        if col != account_col and col != main_amount_col:
            df.drop(columns=[col], inplace=True)
    # rename the columns to standard names
    if account_col:
        df.rename(columns={account_col: "Account"}, inplace=True)
    df.rename(columns={main_amount_col: "Amount"}, inplace=True)
    return df

def clean_excel(file_path):
    """
    high level wrapper function to load an Excel file and return a cleaned DataFrame.
    """
    header_row = determine_header_row(file_path)
    logger.info(f"Determined header row: {header_row}")
    # Read the Excel using the detected header row
    df = pd.read_excel(file_path, header=header_row)
    logger.info(f"Initial read of Excel: {df.shape[0]} rows, {df.shape[1]} columns")
    df_clean = process_dataframe(df)
    logger.info(f"Cleaned DataFrame: {df_clean.shape[0]} rows, {df_clean.shape[1]} columns after cleaning")
    return df_clean
