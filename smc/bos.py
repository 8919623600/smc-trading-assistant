"""
Break of Structure (BOS) Detection
"""

from models import BOSEvent


# ==========================================================
# Helper Functions
# ==========================================================

def _empty_event() -> BOSEvent:
    """
    Returns an empty BOS event.
    """
    return BOSEvent()


# ==========================================================
# Bullish BOS
# ==========================================================

def detect_bullish_bos(df, swing_highs):
    latest_close = float(df.iloc[-1]["close"])

    if not swing_highs:
        return _empty_event()

    last_high = swing_highs[-1]

    if latest_close > last_high.price:
        last_high.broken = True

        return BOSEvent(
            direction="Bullish",
            level=last_high.price,
            time=last_high.time,
            confirmed=True,
        )

    return _empty_event()


# ==========================================================
# Bearish BOS
# ==========================================================

def detect_bearish_bos(df, swing_lows):
    latest_close = float(df.iloc[-1]["close"])

    if not swing_lows:
        return _empty_event()

    last_low = swing_lows[-1]

    if latest_close < last_low.price:
        last_low.broken = True

        return BOSEvent(
            direction="Bearish",
            level=last_low.price,
            time=last_low.time,
            confirmed=True,
        )

    return _empty_event()


# ==========================================================
# Public API
# ==========================================================

def detect_bos(df, swing_highs, swing_lows):
    """
    Detect Break of Structure.
    """

    bullish = detect_bullish_bos(df, swing_highs)

    if bullish.confirmed:
        return bullish

    bearish = detect_bearish_bos(df, swing_lows)

    return bearish