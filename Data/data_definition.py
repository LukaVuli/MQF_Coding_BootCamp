"""
data_definition.py
------------------
DataDefinition is the single entry-point for all data sources in this
codebase.  Instead of calling each source module directly, you create a
DataDefinition object and the class routes your request to the correct
source module.

Supported sources
-----------------
  'famafrench'  Fama-French factor and portfolio data
  'fred'        FRED macro / financial series (NBER recessions, rates …)
  'yfin'        Yahoo Finance OHLCV data (equities, ETFs, indices, FX …)

Usage examples
--------------
>>> from Data.data_definition import DataDefinition
>>>
>>> # List available Fama-French datasets
>>> dd = DataDefinition(source='famafrench', item=None, start=None, end=None)
>>> print(dd.extract())
>>>
>>> # Pull daily FF5 factors
>>> dd = DataDefinition(source='famafrench',
...                     item='F-F_Research_Data_5_Factors_2x3_daily',
...                     start='2000-01-01', end=None)
>>> factors = dd.extract()
>>>
>>> # Pull NBER recession indicator from FRED
>>> dd = DataDefinition(source='fred', item='USRECD',
...                     start='1990-01-01', end=None)
>>> recessions = dd.extract()
>>>
>>> # Pull VIX from Yahoo Finance
>>> dd = DataDefinition(source='yfin', item='^VIX',
...                     start='1990-01-01', end=None)
>>> vix = dd.extract()
"""

from Data.sources import famafrench as _ff
from Data.sources import fred       as _fred
from Data.sources import yahoofin   as _yfin


class DataDefinition:
    """Unified data-access object.

    Parameters
    ----------
    source : str
        One of 'famafrench', 'fred', 'yfin'.
    item : str or None
        Dataset / ticker identifier.  Pass None to list what is
        available for that source.
    start : str or None
        Start date 'YYYY-MM-DD'.
    end : str or None
        End date 'YYYY-MM-DD' (None = most recent available).
    """

    def __init__(self, source: str, item, start, end):
        self.source = source
        self.item   = item
        self.start  = start
        self.end    = end
        self._data  = None
        self._fetch()

    def _fetch(self):
        src = self.source.lower()

        if src == 'famafrench':
            if self.item is None:
                self._data = _ff.available_datasets()
            else:
                self._data = _ff.data_getter(self.item, self.start, self.end)

        elif src == 'fred':
            if self.item is None:
                self._data = _fred.available_series()
            else:
                self._data = _fred.get_series(
                    self.item, self.start or '1900-01-01', self.end
                )

        elif src == 'yfin':
            if self.item is None:
                self._data = _yfin.available_tickers()
            else:
                self._data = _yfin.get_close(
                    self.item, start=self.start, end=self.end
                )

        else:
            raise ValueError(
                f"Unknown source '{self.source}'. "
                f"Choose from: 'famafrench', 'fred', 'yfin'."
            )

    def extract(self):
        """Return the fetched data.

        Returns
        -------
        pd.DataFrame | pd.Series | list | dict
            Depends on the source and item requested.
        """
        return self._data

    def __repr__(self):
        return (
            f"DataDefinition(source='{self.source}', item='{self.item}', "
            f"start='{self.start}', end='{self.end}')"
        )


if __name__ == "__main__":
    dd = DataDefinition('famafrench', item=None, start=None, end=None)
    print("FF datasets (first 5):", dd.extract()[:5])

    dd = DataDefinition('famafrench',
                        item='F-F_Research_Data_5_Factors_2x3',
                        start='2020-01-01', end='2022-12-31')
    print("\nFF5 monthly (head):\n", dd.extract().head())

    dd = DataDefinition('fred', item='USRECD', start='2000-01-01', end=None)
    print("\nUSRECD (tail):\n", dd.extract().tail())
