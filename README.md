# Coding Bootcamp — Starter Codebase

A clean, extensible Python codebase for quantitative finance work.

---

## Table of Contents

1. [Project overview](#1-project-overview)
2. [Folder structure](#2-folder-structure)
3. [Setup](#3-setup)
4. [Running the demo](#4-running-the-demo)
5. [How the codebase is organised](#5-how-the-codebase-is-organised)
   - [Data layer](#data-layer)
   - [Classes layer](#classes-layer)
   - [Utilities layer](#utilities-layer)
6. [Adding a new data source](#6-adding-a-new-data-source)
7. [Adding a new utility function](#7-adding-a-new-utility-function)
8. [Quick reference: common operations](#8-quick-reference-common-operations)

---

## 1. Project overview

The codebase is split into three layers:

| Layer        | Purpose                                                    |
|--------------|------------------------------------------------------------|
| `Data/`      | Raw data ingestion — one module per external source        |
| `Classes/`   | The `DataDefinition` class that wraps every data source    |
| `Utilities/` | Pure helper functions (maths, statistics, date wrangling)  |

`main.py` sits at the root and shows how all three layers work together.

---

## 2. Folder structure

```
Coding_Bootcamp/
│
├── main.py                     ← demo script (run this first)
├── requirements.txt
├── README.md
│
├── Data/
│   ├── data_definition.py      ← DataDefinition: the single entry-point for data
│   └── sources/
│       ├── famafrench.py       ← Fama-French library (via pandas_datareader)
│       ├── fred.py             ← FRED macro data (rates, inflation, recessions …)
│       └── yahoofin.py         ← Yahoo Finance OHLCV (equities, ETFs, indices, VIX …)
│
├── Classes/                    ← (reserved for your own classes)
│
└── Utilities/
    └── tools.py                ← helper functions (returns, levels, stats …)
```

---

## 3. Setup

### 3a. Create a virtual environment (recommended)

```bash
python -m venv .venv
source .venv/bin/activate          # macOS / Linux
.venv\Scripts\activate             # Windows
```

### 3b. Install dependencies

```bash
pip install -r requirements.txt
```

All required packages:

| Package              | Used for                                  |
|----------------------|-------------------------------------------|
| `pandas`             | DataFrames, time-series alignment          |
| `numpy`              | Numerical operations                       |
| `scipy`              | t-statistics in `return_descriptor`        |
| `matplotlib`         | Plotting                                   |
| `pandas_datareader`  | Fama-French & FRED data                    |
| `yfinance`           | Yahoo Finance OHLCV data                   |

---

## 4. Running the demo

```bash
python main.py
```

The script will:

1. Download **Fama-French 5-Factor** daily returns (Mkt-RF, SMB, HML, RMW, CMA).
2. Compute the **growth of $1** invested in each factor since 1990.
3. Download the **NBER recession indicator** from FRED and shade recession periods.
4. Download the **VIX** from Yahoo Finance.
5. Produce a two-panel figure and save it as `ff5_growth_of_dollar.png`.

The chart looks like this:

```
┌─────────────────────────────────────────────────────────┐
│  Growth of $1 — FF5 factors   (log scale, grey = NBER)  │
│                                                          │
│  $100 ┤              ╭──────────╮                        │
│   $10 ┤        ╭─────╯          ╰─────────────────────   │
│    $1 ┤────────╯                                         │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│  VIX                                                     │
│   80 ┤                  ╭╮     ╭╮                        │
│   40 ┤         ╭╮       ││╮    ││                        │
│    0 ┤─────────╯╰───────╯╰─────╯╰──────────────────────  │
└─────────────────────────────────────────────────────────┘
```

---

## 5. How the codebase is organised

### Data layer

`Data/sources/` contains one module per external data provider.  Each module
exposes two things:

1. **`available_*()`** — returns a list or dict of what the source offers.
2. **A retrieval function** — downloads the data and returns a `pd.DataFrame`.

```python
# Direct usage (lower-level)
from Data.sources import famafrench as ff
factors = ff.data_getter('F-F_Research_Data_5_Factors_2x3_daily',
                         start='2000-01-01', end=None)

from Data.sources import fred
recessions = fred.get_series('USRECD', start='1990-01-01')

from Data.sources import yahoofin as yf_src
spy_close = yf_src.get_close('SPY', start='2000-01-01')
```

### Classes layer

`Classes/data_definition.py` provides **`DataDefinition`**, a single unified
interface for all sources.  It accepts a `source` string and an `item`
identifier, fetches the data, and stores it internally.

```python
from Data.data_definition import DataDefinition

# Fama-French 5-Factor daily
dd = DataDefinition(source='famafrench',
                    item='F-F_Research_Data_5_Factors_2x3_daily',
                    start='2000-01-01', end=None)
factors = dd.extract()          # → pd.DataFrame

# FRED series
dd = DataDefinition(source='fred', item='USRECD',
                    start='1990-01-01', end=None)
rec = dd.extract()              # → pd.DataFrame

# Yahoo Finance closing prices
dd = DataDefinition(source='yfin', item='^VIX',
                    start='1990-01-01', end=None)
vix = dd.extract()              # → pd.Series

# Pass item=None to list what is available
dd = DataDefinition(source='fred', item=None, start=None, end=None)
print(dd.extract())             # → dict of common series IDs
```

### Utilities layer

`Utilities/tools.py` contains **pure functions** — no side effects, no global
state.  Import whatever you need:

```python
from Utilities.tools import (
    compute_levels_from_returns,    # (1+r).cumprod()
    compute_returns_from_levels,    # price / price.shift(1) - 1
    return_descriptor,              # annualised stats table
    convert_daily_to_weekly,        # resample to Friday frequency
    generate_date_list,             # list of date strings
)
```

---

## 6. Adding a new data source

**Step 1** — Create `Data/sources/my_source.py`:

```python
# Data/sources/my_source.py

def available_data():
    return ['series_A', 'series_B']

def get_series(item, start, end=None):
    # ... fetch and return a pd.DataFrame / pd.Series
    pass
```

**Step 2** — Register it in `Classes/data_definition.py`.

Find the `_fetch` method and add a new `elif` branch:

```python
elif src == 'my_source':
    if self.item is None:
        self._data = _my_source.available_data()
    else:
        self._data = _my_source.get_series(self.item, self.start, self.end)
```

**Step 3** — Add the import at the top of `data_definition.py`:

```python
from Data.sources import my_source as _my_source
```

That is all.  The `DataDefinition` class now supports `source='my_source'`.

---

## 7. Adding a new utility function

Open `Utilities/tools.py` and add your function.  Follow the existing
convention:

- One clear docstring explaining parameters and return value.
- No global state or I/O — pure computation only.
- Export it from `Utilities/__init__.py` if you want it importable directly
  from the package.

```python
# Utilities/tools.py

def annualise_return(r_periodic, freq):
    """Convert a per-period return to an annualised return.

    Parameters
    ----------
    r_periodic : float
        Return per period (e.g. monthly = 0.01 for 1 %).
    freq : int
        Periods per year (12 for monthly, 252 for daily, 52 for weekly).

    Returns
    -------
    float
    """
    return (1 + r_periodic) ** freq - 1
```

---

## 8. Quick reference: common operations

```python
import pandas as pd
from Classes.data_definition import DataDefinition
from Utilities.tools import (
    compute_levels_from_returns,
    compute_returns_from_levels,
    return_descriptor,
)

# ── Pull FF5 factors (daily) ───────────────────────────────────────────────
dd    = DataDefinition('famafrench', 'F-F_Research_Data_5_Factors_2x3_daily',
                       '2000-01-01', None)
ff5   = dd.extract() / 100.0          # percent → decimal
rets  = ff5[['Mkt-RF','SMB','HML','RMW','CMA']]

# ── Growth of $1 ──────────────────────────────────────────────────────────
levels = compute_levels_from_returns(rets)

# ── Summary stats (annualised, 252 trading days) ──────────────────────────
stats  = return_descriptor(rets, freq=252)
print(stats)

# ── Back out returns from a price series ──────────────────────────────────
prices  = DataDefinition('yfin', 'SPY', '2000-01-01', None).extract()
spy_ret = compute_returns_from_levels(prices)

# ── NBER recession dates ───────────────────────────────────────────────────
rec = DataDefinition('fred', 'USRECD', '2000-01-01', None).extract()
# rec['USRECD'] == 1  →  in a recession

# ── Pull multiple closing prices ───────────────────────────────────────────
from Data.sources.yahoofin import get_multiple_close
prices = get_multiple_close(['SPY', 'TLT', 'GLD'], start='2010-01-01')
```

---

*Happy coding!*
