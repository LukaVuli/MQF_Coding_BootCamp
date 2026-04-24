"""
fred.py
-------
Fetches FRED (Federal Reserve Economic Data) series directly via the
FRED REST API using requests.  Requires a free API key stored in .env
as FRED_API_KEY.  Get one at: https://fred.stlouisfed.org/docs/api/api_key.html

Common series used in this bootcamp
-------------------------------------
USRECD      NBER recession indicator (daily, 1 = recession)
USREC       NBER recession indicator (monthly)
DFF         Fed Funds Effective Rate (daily)
GS10        10-Year Treasury Constant Maturity Rate (monthly)
GS2         2-Year Treasury Constant Maturity Rate (monthly)
CPIAUCSL    Consumer Price Index (monthly)
UNRATE      Unemployment Rate (monthly)
GDP         Gross Domestic Product (quarterly)
DCOILWTICO  WTI Crude Oil Price (daily)
VIXCLS      CBOE VIX closing level (daily)

Usage
-----
>>> from Data.sources import fred
>>> recessions = fred.get_series('USRECD', start='1990-01-01')
"""

import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import requests

from credentials import FRED_API_KEY

_API_URL = "https://api.stlouisfed.org/fred/series/observations"


COMMON_SERIES = {
    'USRECD':       'NBER recession indicator – daily (1 = recession)',
    'USREC':        'NBER recession indicator – monthly (1 = recession)',
    'DFF':          'Fed Funds Effective Rate – daily (%)',
    'GS10':         '10-Year Treasury Constant Maturity – monthly (%)',
    'GS2':          '2-Year Treasury Constant Maturity – monthly (%)',
    'GS1':          '1-Year Treasury Constant Maturity – monthly (%)',
    'TB3MS':        '3-Month Treasury Bill – monthly (%)',
    'BAMLH0A0HYM2': 'ICE BofA US High Yield Option-Adjusted Spread',
    'CPIAUCSL':     'CPI All Urban Consumers – monthly',
    'UNRATE':       'Unemployment Rate – monthly (%)',
    'GDP':          'Gross Domestic Product – quarterly ($B)',
    'DCOILWTICO':   'WTI Crude Oil Price – daily ($/barrel)',
    'VIXCLS':       'CBOE VIX Closing Level – daily',
    'SP500':        'S&P 500 Index – daily',
}


def available_series():
    """Return the quick-reference dict of commonly used FRED series."""
    return COMMON_SERIES


def get_series(series_id: str, start: str = '1900-01-01', end=None) -> pd.DataFrame:
    """Download a FRED series via the REST API.

    Parameters
    ----------
    series_id : str
        FRED series identifier (e.g. 'USRECD', 'GS10').
    start : str
        Start date 'YYYY-MM-DD'.
    end : str or None
        End date.  None = most recent available.

    Returns
    -------
    pd.DataFrame
        Single-column DataFrame indexed by date.
    """
    params = {
        'series_id':           series_id,
        'api_key':             FRED_API_KEY,
        'file_type':           'json',
        'observation_start':   start,
    }
    if end is not None:
        params['observation_end'] = end

    response = requests.get(_API_URL, params=params, timeout=30)

    if response.status_code == 400:
        raise ValueError(
            f"FRED API returned 400 Bad Request for '{series_id}'.\n"
            "Most likely your FRED_API_KEY in .env is still the placeholder 'XXX'.\n"
            "Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html "
            "and paste it into .env as:  FRED_API_KEY=your_key_here"
        )
    response.raise_for_status()

    observations = response.json().get('observations', [])
    if not observations:
        raise ValueError(f"No data returned for FRED series '{series_id}'.")

    df = pd.DataFrame(observations)[['date', 'value']]
    df['date']  = pd.to_datetime(df['date'])
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df = df.set_index('date')
    df.index.name = 'Date'
    df.columns    = [series_id]
    return df


if __name__ == "__main__":
    print("Common FRED series:")
    for k, v in available_series().items():
        print(f"  {k:20s}  {v}")
    print("\nFetching USRECD (last 10 rows):")
    rec = get_series('USRECD', start='2020-01-01')
    print(rec.tail(10))
