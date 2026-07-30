"""
Change of Character (CHoCH) Detection
"""

from models import CHoCHEvent


# ==========================================================
# Helper Functions
# ==========================================================

def _empty_event() -> CHoCHEvent:
    """
    Returns an empty CHoCH event.
    """
    return CHoCHEvent()


# ==========================================================
# Bullish CHoCH
# ==========================================================

def detect_bullish_choch(df, swing_highs, structure):
    """
    Detect bullish Change of Character.
    """
    if structure != "Bearish":
        return _empty_event()

    if not swing_highs:
        return _empty_event()

    latest_close = float(df.iloc[-1]["close"])
    last_high = swing_highs[-1]

    if latest_close > last_high.price:
        return CHoCHEvent(
            direction="Bullish",
            level=last_high.price,
            time=last_high.time,
            confirmed=True,
        )

    return _empty_event()


# ==========================================================
# Bearish CHoCH
# ==========================================================

def detect_bearish_choch(df, swing_lows, structure):
    """
    Detect bearish Change of Character.
    """
    if structure != "Bullish":
        return _empty_event()

    if not swing_lows:
        return _empty_event()

    latest_close = float(df.iloc[-1]["close"])
    last_low = swing_lows[-1]

    if latest_close < last_low.price:
        return CHoCHEvent(
            direction="Bearish",
            level=last_low.price,
            time=last_low.time,
            confirmed=True,
        )

    return _empty_event()


# ==========================================================
# Public API
# ==========================================================

def detect_choch(df, swing_highs, swing_lows, structure):
    """
    Detect Change of Character.
    """

    bullish = detect_bullish_choch(df, swing_highs, structure)

    if bullish.confirmed:
        return bullish

    bearish = detect_bearish_choch(df, swing_lows, structure)

    return bearish