"""
main.py
-------
Bootcamp demonstration script.

What this script does
---------------------
1. Downloads the Fama-French 5-Factor daily returns (Mkt-RF, SMB, HML,
   RMW, CMA) via the ``DataDefinition`` class.
2. Converts the percentage returns to decimal and computes the growth of
   $1 invested in each factor since the start of the sample.
3. Downloads the NBER recession indicator (daily) from FRED and shades
   recession periods on the chart.
4. Downloads the VIX from Yahoo Finance and plots it in a second panel.
5. Saves the figure as ``ff5_growth_of_dollar.png``.

Run
---
    python main.py

Dependencies
------------
    pip install pandas numpy matplotlib pandas_datareader yfinance scipy
"""

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

# ── project imports ────────────────────────────────────────────────────────
from Data.data_definition import DataDefinition
from Utilities.tools import (
    compute_levels_from_returns,
    return_descriptor,
)
from pathlib import Path

# ── configuration ──────────────────────────────────────────────────────────
START_DATE  = '1990-01-01'   # beginning of the analysis window
END_DATE    = None            # None  →  most recent available data
SAVE_FIGURE = True
FIGURE_PATH = Path.home() / 'Desktop' / 'ff5_growth_of_dollar.png'
FREQ        = 252             # trading days per year (for annualisation)

FACTOR_COLORS = {
    'Mkt-RF': '#1f77b4',   # blue
    'SMB':    '#ff7f0e',   # orange
    'HML':    '#2ca02c',   # green
    'RMW':    '#d62728',   # red
    'CMA':    '#9467bd',   # purple
}

FACTOR_LABELS = {
    'Mkt-RF': 'Market (Mkt-RF)',
    'SMB':    'Size (SMB)',
    'HML':    'Value (HML)',
    'RMW':    'Profitability (RMW)',
    'CMA':    'Investment (CMA)',
}


# ===========================================================================
# Helper functions
# ===========================================================================

def shade_recessions(ax, usrecd: pd.DataFrame):
    """Draw grey shading over NBER recession periods on *ax*.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
    usrecd : pd.DataFrame
        Single-column DataFrame with the USRECD series (1 = recession).
    """
    col          = usrecd.columns[0]
    in_recession = False
    rec_start    = None

    for date, val in usrecd[col].items():
        if val == 1 and not in_recession:
            in_recession = True
            rec_start    = date
        elif val == 0 and in_recession:
            in_recession = False
            ax.axvspan(rec_start, date, color='grey', alpha=0.15,
                       zorder=0, label='_nolegend_')

    # Handle data that ends mid-recession
    if in_recession and rec_start is not None:
        ax.axvspan(rec_start, usrecd.index[-1], color='grey', alpha=0.15,
                   zorder=0, label='_nolegend_')


# ===========================================================================
# Main routine
# ===========================================================================

def main():

    # -----------------------------------------------------------------------
    # 1.  Fama-French 5-Factor daily returns
    # -----------------------------------------------------------------------
    print("► Fetching Fama-French 5-Factor daily data …", end=' ')
    dd_ff5 = DataDefinition(
        source='famafrench',
        item='F-F_Research_Data_5_Factors_2x3_daily',
        start=START_DATE,
        end=END_DATE,
    )
    ff5_raw = dd_ff5.extract()
    print("done.")

    # The raw data is in percentage points — convert to decimals
    ff5 = ff5_raw / 100.0

    # Keep only the five long-short factor columns
    factors = list(FACTOR_COLORS.keys())   # ['Mkt-RF','SMB','HML','RMW','CMA']
    ff5 = ff5[factors].copy()

    # Drop any rows that are all NaN (can occur at boundaries)
    ff5.dropna(how='all', inplace=True)

    # -----------------------------------------------------------------------
    # 2.  Growth of $1
    # -----------------------------------------------------------------------
    print("► Computing growth of $1 …", end=' ')
    levels = compute_levels_from_returns(ff5)
    print("done.")

    # -----------------------------------------------------------------------
    # 3.  Descriptive statistics
    # -----------------------------------------------------------------------
    print("\n── Annualised factor statistics ──────────────────────────────")
    stats = return_descriptor(ff5.dropna(), freq=FREQ)
    pd.set_option('display.float_format', '{:.4f}'.format)
    print(stats.loc[['Annualized mu', 'Annualized std', 'Sharpe',
                      'skewness', 'kurtosis']].to_string())
    print()

    # -----------------------------------------------------------------------
    # 4.  NBER recession indicator from FRED
    # -----------------------------------------------------------------------
    print("► Fetching NBER recession data from FRED …", end=' ')
    dd_rec = DataDefinition(
        source='fred',
        item='USRECD',
        start=START_DATE,
        end=END_DATE,
    )
    usrecd = dd_rec.extract()
    print("done.")

    # -----------------------------------------------------------------------
    # 5.  VIX from Yahoo Finance
    # -----------------------------------------------------------------------
    print("► Fetching VIX from Yahoo Finance …", end=' ')
    dd_vix = DataDefinition(
        source='yfin',
        item='^VIX',
        start=START_DATE,
        end=END_DATE,
    )
    vix = dd_vix.extract().rename('^VIX')
    print("done.")

    # -----------------------------------------------------------------------
    # 6.  Align date ranges to the FF5 window
    # -----------------------------------------------------------------------
    t0, t1 = levels.index[0], levels.index[-1]

    usrecd_plot = usrecd.loc[t0:t1]
    vix_plot    = vix.loc[t0:t1]

    # -----------------------------------------------------------------------
    # 7.  Plot
    # -----------------------------------------------------------------------
    print("► Building chart …", end=' ')

    fig = plt.figure(figsize=(15, 9))
    gs  = GridSpec(2, 1, figure=fig,
                   height_ratios=[3, 1],
                   hspace=0.04)          # tiny gap between panels

    ax_top = fig.add_subplot(gs[0])
    ax_bot = fig.add_subplot(gs[1], sharex=ax_top)

    # ── Top panel: Growth of $1 ──────────────────────────────────────────
    for factor, color in FACTOR_COLORS.items():
        ax_top.plot(
            levels.index,
            levels[factor],
            label=FACTOR_LABELS[factor],
            color=color,
            linewidth=1.4,
            alpha=0.9,
        )

    shade_recessions(ax_top, usrecd_plot)

    ax_top.set_yscale('log')
    ax_top.set_ylabel('Growth of $1  (log scale)', fontsize=12)
    ax_top.set_title(
        'Fama-French 5 Factors — Growth of $1 with NBER Recession Shading',
        fontsize=14, fontweight='bold', pad=12,
    )
    ax_top.grid(True, which='both', alpha=0.25, linestyle='--')
    ax_top.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda y, _: f'${y:.2f}')
    )

    # Build a custom legend that includes the recession patch
    rec_patch = mpatches.Patch(color='grey', alpha=0.35, label='NBER Recession')
    handles, labels_ = ax_top.get_legend_handles_labels()
    ax_top.legend(handles + [rec_patch], labels_ + ['NBER Recession'],
                  loc='upper left', fontsize=10, framealpha=0.9)

    plt.setp(ax_top.get_xticklabels(), visible=False)  # share x-axis with bottom

    # ── Bottom panel: VIX ───────────────────────────────────────────────
    ax_bot.fill_between(vix_plot.index, vix_plot.values,
                        color='#7f7f7f', alpha=0.5, label='VIX')
    ax_bot.plot(vix_plot.index, vix_plot.values,
                color='black', linewidth=0.8, alpha=0.8)

    shade_recessions(ax_bot, usrecd_plot)

    # Annotate notable VIX spikes
    notable = {
        '2008-11-20': 'GFC',
        '2020-03-18': 'COVID',
    }
    for date_str, label in notable.items():
        dt = pd.Timestamp(date_str)
        if dt in vix_plot.index:
            spike = vix_plot.loc[dt]
            ax_bot.annotate(
                label,
                xy=(dt, spike),
                xytext=(0, 10),
                textcoords='offset points',
                fontsize=8,
                ha='center',
                arrowprops=dict(arrowstyle='->', color='black', lw=0.8),
            )

    ax_bot.set_ylabel('VIX', fontsize=12)
    ax_bot.set_xlabel('Date', fontsize=12)
    ax_bot.set_ylim(bottom=0)
    ax_bot.grid(True, alpha=0.25, linestyle='--')
    ax_bot.legend(loc='upper left', fontsize=10, framealpha=0.9)

    # ── Save & show ──────────────────────────────────────────────────────
    plt.tight_layout()

    if SAVE_FIGURE:
        fig.savefig(FIGURE_PATH, dpi=150, bbox_inches='tight')
        print(f"done.\n► Figure saved → {FIGURE_PATH}")
        plt.close(fig)
    else:
        print("done.")
        plt.show()


# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == "__main__":
    main()
