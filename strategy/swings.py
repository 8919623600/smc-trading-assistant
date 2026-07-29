from models import SwingPoint
from config import LOOKBACK, MAX_STRENGTH_LOOKBACK


def calculate_strength(values, index, is_high):
    """
    Calculate how significant a swing is.

    The larger the window where the point remains the highest
    (or lowest), the stronger the swing.
    """

    strength = 1

    for window in range(LOOKBACK + 1, MAX_STRENGTH_LOOKBACK + 1):

        if index - window < 0 or index + window >= len(values):
            break

        section = values[index - window:index + window + 1]

        if is_high:
            if values[index] == max(section):
                strength += 1
            else:
                break
        else:
            if values[index] == min(section):
                strength += 1
            else:
                break

    return strength


def find_swings(df, lookback=LOOKBACK):

    swing_highs = []
    swing_lows = []

    highs = df["high"].values
    lows = df["low"].values

    for i in range(lookback, len(df) - lookback):

        current_high = highs[i]
        current_low = lows[i]

        high_window = highs[i - lookback:i + lookback + 1]
        low_window = lows[i - lookback:i + lookback + 1]

        # Swing High
        if (
            current_high == max(high_window)
            and list(high_window).count(current_high) == 1
        ):
            strength = calculate_strength(highs, i, True)

            swing_highs.append(
                SwingPoint(
                    time=df.index[i],
                    price=float(current_high),
                    swing_type="HIGH",
                    strength=strength,
                )
            )

        # Swing Low
        if (
            current_low == min(low_window)
            and list(low_window).count(current_low) == 1
        ):
            strength = calculate_strength(lows, i, False)

            swing_lows.append(
                SwingPoint(
                    time=df.index[i],
                    price=float(current_low),
                    swing_type="LOW",
                    strength=strength,
                )
            )

    return swing_highs, swing_lows
