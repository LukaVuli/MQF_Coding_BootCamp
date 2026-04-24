"""
famafrench.py
-------------
Downloads Fama-French datasets directly from Kenneth French's data library
at Dartmouth (no pandas_datareader required).

Data is fetched as a zip file, extracted, and parsed into a DataFrame.
Returns are in percentage points — divide by 100 to get decimals.

Usage
-----
>>> from Data.sources import famafrench as ff
>>> factors = ff.data_getter('F-F_Research_Data_5_Factors_2x3_daily',
...                          start='2000-01-01', end=None)
"""

import io
import warnings
import zipfile

import pandas as pd
import requests

warnings.filterwarnings('ignore')

_BASE_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/{dataset}_CSV.zip"


# ---------------------------------------------------------------------------
# Dataset catalogue
# ---------------------------------------------------------------------------

def available_datasets():
    """Return the list of supported Fama-French dataset names."""
    return [
        # ---- 3-Factor ----
        'F-F_Research_Data_Factors',
        'F-F_Research_Data_Factors_weekly',
        'F-F_Research_Data_Factors_daily',
        # ---- 5-Factor ----
        'F-F_Research_Data_5_Factors_2x3',
        'F-F_Research_Data_5_Factors_2x3_daily',
        # ---- Momentum ----
        'F-F_Momentum_Factor',
        'F-F_Momentum_Factor_daily',
        # ---- Size-sorted portfolios ----
        'Portfolios_Formed_on_ME',
        'Portfolios_Formed_on_ME_Daily',
        # ---- Book-to-market ----
        'Portfolios_Formed_on_BE-ME',
        'Portfolios_Formed_on_BE-ME_Daily',
        # ---- Profitability ----
        'Portfolios_Formed_on_OP',
        'Portfolios_Formed_on_OP_Daily',
        # ---- Investment ----
        'Portfolios_Formed_on_INV',
        'Portfolios_Formed_on_INV_Daily',
        # ---- 6 / 25 / 100 Portfolios ----
        '6_Portfolios_2x3',
        '6_Portfolios_2x3_daily',
        '25_Portfolios_5x5',
        '25_Portfolios_5x5_Daily',
        '100_Portfolios_10x10',
        '100_Portfolios_10x10_Daily',
        # ---- Industry portfolios ----
        '5_Industry_Portfolios',
        '5_Industry_Portfolios_daily',
        '10_Industry_Portfolios',
        '10_Industry_Portfolios_daily',
        '12_Industry_Portfolios',
        '12_Industry_Portfolios_daily',
        '17_Industry_Portfolios',
        '17_Industry_Portfolios_daily',
        '30_Industry_Portfolios',
        '30_Industry_Portfolios_daily',
        '48_Industry_Portfolios',
        '48_Industry_Portfolios_daily',
        '49_Industry_Portfolios',
        '49_Industry_Portfolios_daily',
        # ---- International ----
        'Developed_3_Factors',
        'Developed_3_Factors_Daily',
        'Developed_5_Factors',
        'Developed_5_Factors_Daily',
        'Europe_3_Factors',
        'Europe_3_Factors_Daily',
        'Japan_3_Factors',
        'Japan_3_Factors_Daily',
        'North_America_3_Factors',
        'North_America_3_Factors_Daily',
        'Emerging_5_Factors',
        'Emerging_MOM_Factor',
    ]


# ---------------------------------------------------------------------------
# Internal parser
# ---------------------------------------------------------------------------

def _parse_fama_french(raw: str, start=None, end=None) -> pd.DataFrame:
    """Parse the raw text from a Ken French CSV/zip file.

    French files are comma-separated with:
      - Plain-text description at the top
      - A header row (may start with a leading comma, e.g. ',Mkt-RF,SMB,...')
      - Data rows whose first token is a 6- (monthly) or 8-digit (daily) date
      - A blank line marking the end of the first table
      - Optional annual summary tables below (ignored)
    """
    lines = raw.splitlines()

    # ── Locate the first data row ─────────────────────────────────────────
    data_start = None
    date_len   = None

    for i, line in enumerate(lines):
        parts = [p.strip() for p in line.split(',')]
        if not parts:
            continue
        tok = parts[0]
        if tok.isdigit() and len(tok) in (6, 8):
            data_start = i
            date_len   = len(tok)
            break

    if data_start is None:
        raise ValueError("Could not locate data rows in the Fama-French file.")

    # ── Find the column-header row (last non-empty line before data) ──────
    # The header often starts with an empty field: ',Mkt-RF,SMB,...'
    header = None
    for i in range(data_start - 1, -1, -1):
        stripped = lines[i].strip()
        if not stripped:
            continue
        parts = [p.strip() for p in stripped.split(',')]
        non_empty = [p for p in parts if p]
        if non_empty and not non_empty[0].isdigit():
            header = non_empty
            break

    # ── Read data rows (stop at blank line or non-date first token) ───────
    rows = []
    for line in lines[data_start:]:
        parts = [p.strip() for p in line.split(',')]
        if not parts or not parts[0]:
            break                                    # end of first table
        tok = parts[0]
        if tok.isdigit() and len(tok) == date_len:
            rows.append(parts)
        else:
            break                                    # hit annual summary

    if not rows:
        raise ValueError("No data rows found in Fama-French file.")

    # ── Build DataFrame ───────────────────────────────────────────────────
    df = pd.DataFrame(rows)

    # Assign column names
    n_data_cols = df.shape[1] - 1          # exclude the date column
    if header and len(header) == n_data_cols:
        df.columns = ['Date'] + header
    elif header and len(header) == df.shape[1]:
        df.columns = header
    else:
        df.columns = ['Date'] + [f'col{k}' for k in range(n_data_cols)]

    # Parse dates
    fmt = '%Y%m%d' if date_len == 8 else '%Y%m'
    df.index      = pd.to_datetime(df['Date'], format=fmt)
    df.index.name = 'Date'
    df            = df.drop(columns=['Date'])
    df            = df.apply(pd.to_numeric, errors='coerce')

    # Filter date range
    if start:
        df = df[df.index >= pd.Timestamp(start)]
    if end:
        df = df[df.index <= pd.Timestamp(end)]

    return df


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def data_getter(dataset: str, start, end=None) -> pd.DataFrame:
    """Download a Fama-French dataset directly from Kenneth French's website.

    Parameters
    ----------
    dataset : str
        Dataset name (see available_datasets()).
    start : str
        Start date 'YYYY-MM-DD'.
    end : str or None
        End date.  None = most recent available.

    Returns
    -------
    pd.DataFrame
        Returns in percentage points (divide by 100 for decimals).
    """
    url = _BASE_URL.format(dataset=dataset)
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        csv_name = next(
            n for n in zf.namelist()
            if n.upper().endswith('.CSV')
        )
        raw = zf.read(csv_name).decode('latin-1')

    return _parse_fama_french(raw, start=start, end=end)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Available datasets (first 5):", available_datasets()[:5])
    factors = data_getter('F-F_Research_Data_5_Factors_2x3_daily',
                          start='2020-01-01', end='2020-03-31')
    print("\nFF5 daily (head):\n", factors.head())
    print("Shape:", factors.shape)
