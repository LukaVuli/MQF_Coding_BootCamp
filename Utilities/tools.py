"""
tools.py
--------
Core utility functions for data manipulation, return/level conversions,
and summary statistics.  These helpers are used throughout the bootcamp
exercises and are intentionally kept small and composable.
"""

import pandas as pd
import numpy as np
import numpy.random as random
from scipy import stats


# ---------------------------------------------------------------------------
# Frequency conversion
# ---------------------------------------------------------------------------

def convert_daily_to_weekly(data):
    """Resample daily data to weekly (Friday) frequency without dropping observations.

    Parameters
    ----------
    data : pd.DataFrame or pd.Series
        Time-series with a DatetimeIndex at daily frequency.

    Returns
    -------
    pd.DataFrame or pd.Series
        Weekly (Friday) frequency time-series.
    """
    data_beg_date = data.index[1]
    data_end_date = data.index[-1]
    data_daily_dates  = pd.date_range(start=data_beg_date, end=data_end_date, freq='D')
    data_weekly_dates = pd.date_range(start=data_beg_date, end=data_end_date, freq='W-FRI')
    data_weekly = data.reindex(index=data_daily_dates).ffill()
    data_weekly = data_weekly.reindex(index=data_weekly_dates)
    return data_weekly


# ---------------------------------------------------------------------------
# Return / level conversions
# ---------------------------------------------------------------------------

def compute_levels_from_returns(returns):
    """Compound simple returns forward into an index starting at 1.

    Parameters
    ----------
    returns : pd.DataFrame or pd.Series
        Simple (arithmetic) returns.

    Returns
    -------
    pd.DataFrame or pd.Series
        Cumulative product index (starts near 1 at the first period).
    """
    return (1.0 + returns).cumprod()


def compute_levels_from_returns_inverse(returns):
    """Compound returns backward so the index ends at 1 (useful for drawdown charts).

    Parameters
    ----------
    returns : pd.DataFrame or pd.Series

    Returns
    -------
    pd.DataFrame or pd.Series
    """
    dcum   = (1.0 + returns).cumprod()
    result = dcum.div(dcum.iloc[-1])
    return result


def compute_returns_from_levels(levels):
    """Compute simple period returns from a price/index series.

    Parameters
    ----------
    levels : pd.DataFrame or pd.Series

    Returns
    -------
    pd.DataFrame or pd.Series
    """
    return levels / levels.shift(1) - 1.0


def compute_returns_from_levels_mixed_freq(levels):
    """Compute returns for a DataFrame whose columns may have different start dates.

    NaN values at the beginning or end of each column are stripped before
    computing returns, then the full index is restored.

    Parameters
    ----------
    levels : pd.DataFrame

    Returns
    -------
    pd.DataFrame
    """
    returns = {}
    for c in levels.columns:
        _levs = levels[c].copy(deep=True).dropna()
        _rets = compute_returns_from_levels(_levs)
        returns[c] = _rets
    return pd.DataFrame(returns)


# ---------------------------------------------------------------------------
# Index / date helpers
# ---------------------------------------------------------------------------

def find_beg_end_dataframe(data, drop_method):
    """Return the first and last date after dropping rows with NaN.

    Parameters
    ----------
    data : pd.DataFrame
    drop_method : str
        'any' or 'all' – passed to DataFrame.dropna(how=...).

    Returns
    -------
    (Timestamp, Timestamp) or (None, None)
    """
    assert isinstance(data, pd.DataFrame)
    truncated = data.dropna(how=drop_method)
    if not truncated.empty:
        return truncated.index.min(), truncated.index.max()
    return None, None


def find_beg_end_series(data, arg=None):
    """Return the first and/or last non-NaN date of a Series.

    Parameters
    ----------
    data : pd.Series
    arg : {None, 'beg_only', 'end_only'}

    Returns
    -------
    (Timestamp or None, Timestamp or None)
    """
    assert isinstance(data, pd.Series), "Only pandas Series can be handled."
    truncated = data.dropna()
    if not truncated.empty:
        if arg == 'beg_only':
            return truncated.index.min(), None
        elif arg == 'end_only':
            return None, truncated.index.max()
        else:
            return truncated.index.min(), truncated.index.max()
    return None, None


# ---------------------------------------------------------------------------
# Missing-value helpers
# ---------------------------------------------------------------------------

def fill_interior(data, method=None, value=None, arg=None):
    """Fill NaN values inside the valid range of each column.

    Values before the first valid observation and after the last are left
    as NaN so that the original DataFrame shape is preserved.

    Parameters
    ----------
    data : pd.DataFrame
    method : {'ffill', 'bfill', None}
        Fill method.  Pass None and use value= for a constant fill.
    value : scalar or None
        Replacement value when method is None.
    arg : {None, 'beg_only', 'end_only'}
        Passed to find_beg_end_series.

    Returns
    -------
    pd.DataFrame
    """
    output = {}
    for c in data.columns:
        beg_dt, end_dt = find_beg_end_series(data=data[c], arg=arg)
        if method == 'ffill':
            filled = data[c].ffill()
        elif method == 'bfill':
            filled = data[c].bfill()
        else:
            filled = data[c].fillna(value=value)
        filled = filled.truncate(before=beg_dt, after=end_dt)
        output[c] = filled

    output = pd.DataFrame(output)
    output = output.reindex(index=data.index, columns=data.columns)
    return output


def fill_interior_series(data, method=None, value=None, arg=None):
    """Same as fill_interior but for a single Series.

    Parameters
    ----------
    data : pd.Series
    method : {'ffill', 'bfill', None}
    value : scalar or None
    arg : {None, 'beg_only', 'end_only'}

    Returns
    -------
    pd.Series
    """
    beg_dt, end_dt = find_beg_end_series(data=data, arg=arg)
    if method == 'ffill':
        filled = data.ffill()
    elif method == 'bfill':
        filled = data.bfill()
    else:
        filled = data.fillna(value=value)
    filled = filled.truncate(before=beg_dt, after=end_dt)
    filled = filled.reindex(index=data.index)
    return filled


def ffill_na(data, value):
    """Forward-fill NaN gaps from each column's first valid observation.

    Parameters
    ----------
    data : pd.DataFrame
    value : scalar
        Fallback fill value used where method is None.

    Returns
    -------
    pd.DataFrame
    """
    return fill_interior(data=data, method=None, value=value, arg='beg_only')


def fillna_random(series):
    """Replace NaN values with tiny random noise (useful to avoid singular matrices).

    Parameters
    ----------
    series : pd.Series

    Returns
    -------
    pd.Series
    """
    a    = series.values.copy()
    mask = np.isnan(a)
    a[mask] = np.array([random.uniform(1e-20, 1e-17) for _ in range(mask.sum())])
    return pd.Series(a, index=series.index, name=series.name)


# ---------------------------------------------------------------------------
# Descriptive statistics
# ---------------------------------------------------------------------------

def return_descriptor(df, freq):
    """Compute annualised summary statistics for a returns DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Returns (not yet annualised).
    freq : int
        Observations per year (252 for daily, 52 for weekly, 12 for monthly).

    Returns
    -------
    pd.DataFrame
        Transposed stats table with one column per asset.
    """
    mean     = df.mean()  * freq
    t_stat, p_value = stats.ttest_1samp(df, 0, nan_policy='omit')
    std_dev  = df.std()   * np.sqrt(freq)
    q25      = df.quantile(0.25)
    q50      = df.quantile(0.50)
    q75      = df.quantile(0.75)
    maximum  = df.max()
    minimum  = df.min()
    skewness = df.skew()
    kurtosis = df.kurt()
    sharpe   = mean / std_dev

    stats_df = pd.DataFrame({
        'Annualized mu':  mean,
        't-stat':         t_stat,
        'p-value':        p_value,
        'Annualized std': std_dev,
        'Sharpe':         sharpe,
        'min':            minimum,
        '25%':            q25,
        '50%':            q50,
        '75%':            q75,
        'max':            maximum,
        'skewness':       skewness,
        'kurtosis':       kurtosis,
    })
    return stats_df.T


# ---------------------------------------------------------------------------
# Date-list generator
# ---------------------------------------------------------------------------

def generate_date_list(start_date, end_date, freq):
    """Return a list of date strings between two dates at a given frequency.

    Parameters
    ----------
    start_date : str
    end_date : str
    freq : str
        Pandas offset alias, e.g. 'D', 'W-FRI', 'MS'.

    Returns
    -------
    list[str]
        Dates formatted as 'YYYY-MM-DD'.
    """
    date_range = pd.date_range(start=start_date, end=end_date, freq=freq)
    return date_range.strftime('%Y-%m-%d').tolist()


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    rng  = np.random.default_rng(42)
    rets = pd.Series(rng.normal(0.0005, 0.01, 252))
    lvls = compute_levels_from_returns(rets)
    desc = return_descriptor(rets.to_frame(name='test'), freq=252)
    print("Levels (last 5):\n", lvls.tail())
    print("\nDescriptive stats:\n", desc)
