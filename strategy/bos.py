from models import SwingPoint


def detect_bos(df, swing_highs, swing_lows):
    """
    Detect the latest confirmed Break of Structure (BOS).

    Returns:
        {
            "direction": "Bullish" | "Bearish" | None,
            "level": float | None,
            "time": timestamp | None
        }
    """

    latest_close = float(df.iloc[-1]["close"])

    # Check bullish BOS
    if swing_highs:
        last_high = swing_highs[-1]

        if latest_close > last_high.price:
            last_high.broken = True

            return {
                "direction": "Bullish",
                "level": last_high.price,
                "time": last_high.time,
            }

    # Check bearish BOS
    if swing_lows:
        last_low = swing_lows[-1]

        if latest_close < last_low.price:
            last_low.broken = True

            return {
                "direction": "Bearish",
                "level": last_low.price,
                "time": last_low.time,
            }

    return {
        "direction": None,
        "level": None,
        "time": None,
    }
