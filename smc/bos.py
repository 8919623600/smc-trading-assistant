"""
smc/bos.py

Break Of Structure (BOS) detection engine.

Author: BMIE Project
"""

from typing import Dict, List

from models import SwingPoint


# ==========================================================
# Bullish BOS
# ==========================================================

def detect_bullish_bos(
    latest_close: float,
    swing_highs: List[SwingPoint],
) -> Dict:
    """
    Detect bullish Break of Structure.
    """

    if not swing_highs:
        return {}

    last_high = swing_highs[-1]

    if latest_close > last_high.price:

        last_high.broken = True

        return {
            "direction": "Bullish",
            "level": last_high.price,
            "time": last_high.time,
        }

    return {}


# ==========================================================
# Bearish BOS
# ==========================================================

def detect_bearish_bos(
    latest_close: float,
    swing_lows: List[SwingPoint],
) -> Dict:
    """
    Detect bearish Break of Structure.
    """

    if not swing_lows:
        return {}

    last_low = swing_lows[-1]

    if latest_close < last_low.price:

        last_low.broken = True

        return {
            "direction": "Bearish",
            "level": last_low.price,
            "time": last_low.time,
        }

    return {}


# ==========================================================
# Main BOS Detection
# ==========================================================

def detect_bos(
    df,
    swing_highs: List[SwingPoint],
    swing_lows: List[SwingPoint],
) -> Dict:
    """
    Detect the latest confirmed Break of Structure.
    """

    latest_close = float(df.iloc[-1]["close"])

    bullish = detect_bullish_bos(
        latest_close,
        swing_highs,
    )

    if bullish:
        return bullish

    bearish = detect_bearish_bos(
        latest_close,
        swing_lows,
    )

    if bearish:
        return bearish

    return {
        "direction": None,
        "level": None,
        "time": None,
    }