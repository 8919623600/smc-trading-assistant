"""
smc/choch.py

Change of Character (CHoCH) Detection

A CHoCH is detected when price breaks the most recent
significant swing against the current market structure.

Bullish Structure:
    Bearish -> Bullish transition

Bearish Structure:
    Bullish -> Bearish transition
"""

from typing import Dict, List

from models import SwingPoint


def _empty_result() -> Dict:
    """
    Return an empty CHoCH result.
    """

    return {
        "direction": None,
        "level": None,
        "time": None,
    }


def detect_bullish_choch(
    latest_close: float,
    swing_highs: List[SwingPoint],
) -> Dict:
    """
    Detect Bullish CHoCH.

    Bullish CHoCH occurs when price closes above
    the latest swing high.
    """

    if not swing_highs:
        return _empty_result()

    last_high = swing_highs[-1]

    if latest_close > last_high.price:

        return {
            "direction": "Bullish",
            "level": last_high.price,
            "time": last_high.time,
        }

    return _empty_result()


def detect_bearish_choch(
    latest_close: float,
    swing_lows: List[SwingPoint],
) -> Dict:
    """
    Detect Bearish CHoCH.

    Bearish CHoCH occurs when price closes below
    the latest swing low.
    """

    if not swing_lows:
        return _empty_result()

    last_low = swing_lows[-1]

    if latest_close < last_low.price:

        return {
            "direction": "Bearish",
            "level": last_low.price,
            "time": last_low.time,
        }

    return _empty_result()


def detect_choch(
    df,
    swing_highs: List[SwingPoint],
    swing_lows: List[SwingPoint],
    structure: str,
) -> Dict:
    """
    Detect Change of Character.

    Parameters
    ----------
    df
        Market OHLC data.
    swing_highs
        List of detected swing highs.
    swing_lows
        List of detected swing lows.
    structure
        Current market structure.

    Returns
    -------
    dict
        CHoCH information.
    """

    latest_close = float(df.iloc[-1]["close"])

    if structure == "Bearish":
        return detect_bullish_choch(
            latest_close,
            swing_highs,
        )

    if structure == "Bullish":
        return detect_bearish_choch(
            latest_close,
            swing_lows,
        )

    return _empty_result()