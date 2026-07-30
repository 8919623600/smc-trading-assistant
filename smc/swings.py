"""
smc/swings.py

Swing detection engine for BMIE.

This module identifies swing highs and swing lows and calculates
their relative strength. Strong swings are automatically marked
as major swings for use by higher-level Smart Money Concept
algorithms.

Author: BMIE Project
"""

from typing import List, Tuple

from config import LOOKBACK, MAX_STRENGTH_LOOKBACK
from models import SwingPoint


# ==========================================================
# Swing Strength
# ==========================================================

def calculate_strength(
    values,
    index: int,
    is_high: bool,
) -> int:
    """
    Calculate the strength of a swing.

    A swing becomes stronger if it remains the highest
    (or lowest) over progressively larger windows.
    """

    strength = 1

    for window in range(
        LOOKBACK + 1,
        MAX_STRENGTH_LOOKBACK + 1,
    ):

        if index - window < 0:
            break

        if index + window >= len(values):
            break

        section = values[index - window:index + window + 1]

        if is_high:

            if values[index] != max(section):
                break

        else:

            if values[index] != min(section):
                break

        strength += 1

    return strength


# ==========================================================
# Major Swing Detection
# ==========================================================

def mark_major_swings(
    swings: List[SwingPoint],
) -> None:
    """
    Mark stronger swings as major swings.

    This threshold can later be moved into config.py.
    """

    for swing in swings:

        if swing.strength >= 3:
            swing.major = True


# ==========================================================
# Swing Detection
# ==========================================================

def find_swings(
    df,
    lookback: int = LOOKBACK,
) -> Tuple[List[SwingPoint], List[SwingPoint]]:
    """
    Detect swing highs and swing lows.
    """

    swing_highs: List[SwingPoint] = []
    swing_lows: List[SwingPoint] = []

    highs = df["high"].values
    lows = df["low"].values

    for i in range(
        lookback,
        len(df) - lookback,
    ):

        current_high = highs[i]
        current_low = lows[i]

        high_window = highs[
            i - lookback:i + lookback + 1
        ]

        low_window = lows[
            i - lookback:i + lookback + 1
        ]

        # ----------------------------------------------
        # Swing High
        # ----------------------------------------------

        if (
            current_high == max(high_window)
            and list(high_window).count(current_high) == 1
        ):

            swing_highs.append(

                SwingPoint(
                    time=df.index[i],
                    price=float(current_high),
                    swing_type="HIGH",
                    strength=calculate_strength(
                        highs,
                        i,
                        True,
                    ),
                )
            )

        # ----------------------------------------------
        # Swing Low
        # ----------------------------------------------

        if (
            current_low == min(low_window)
            and list(low_window).count(current_low) == 1
        ):

            swing_lows.append(

                SwingPoint(
                    time=df.index[i],
                    price=float(current_low),
                    swing_type="LOW",
                    strength=calculate_strength(
                        lows,
                        i,
                        False,
                    ),
                )
            )

    # Identify major swings
    mark_major_swings(swing_highs)
    mark_major_swings(swing_lows)

    return swing_highs, swing_lows