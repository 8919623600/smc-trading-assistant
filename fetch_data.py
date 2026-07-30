"""
fetch_data.py

Downloads historical market data from TradingView.

This module is the only place responsible for
communicating with TradingView.

Author: BMIE Project
"""

from tvDatafeed import TvDatafeed, Interval

from config import DEFAULT_BARS
from core.session import TradingSession

# ==========================================================
# TradingView Connection
# ==========================================================

tv = TvDatafeed()

# ==========================================================
# Supported Timeframes
# ==========================================================

INTERVALS = {
    "1m": Interval.in_1_minute,
    "5m": Interval.in_5_minute,
    "15m": Interval.in_15_minute,
    "30m": Interval.in_30_minute,
    "1h": Interval.in_1_hour,
    "4h": Interval.in_4_hour,
    "1d": Interval.in_daily,
}


# ==========================================================
# Market Data
# ==========================================================

def get_data(
    session: TradingSession,
    timeframe: str,
    bars: int = DEFAULT_BARS,
):
    """
    Download historical data for the current trading session.

    Parameters
    ----------
    session : TradingSession
        Active trading session.

    timeframe : str
        Chart timeframe.

    bars : int
        Number of candles.

    Returns
    -------
    pandas.DataFrame
    """

    if timeframe not in INTERVALS:
        raise ValueError(
            f"Unsupported timeframe: {timeframe}"
        )

    data = tv.get_hist(
        symbol=session.symbol,
        exchange=session.exchange,
        interval=INTERVALS[timeframe],
        n_bars=bars,
    )

    if data is None or data.empty:
        raise RuntimeError(
            f"No data found for "
            f"{session.symbol} ({timeframe})"
        )

    return data