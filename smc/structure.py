"""
smc/structure.py

Market Structure Engine for BMIE.

This module labels swing highs and swing lows and determines
the current market structure.

Author: BMIE Project
"""

from typing import List, Tuple

from models import SwingPoint


# ==========================================================
# Swing High Labels
# ==========================================================

def label_highs(
    swing_highs: List[SwingPoint],
) -> None:
    """
    Label swing highs as:
    START, HH, LH or EH.
    """

    previous_high = None

    for swing in swing_highs:

        if previous_high is None:

            swing.label = "START"

        elif swing.price > previous_high:

            swing.label = "HH"

        elif swing.price < previous_high:

            swing.label = "LH"

        else:

            swing.label = "EH"

        previous_high = swing.price


# ==========================================================
# Swing Low Labels
# ==========================================================

def label_lows(
    swing_lows: List[SwingPoint],
) -> None:
    """
    Label swing lows as:
    START, HL, LL or EL.
    """

    previous_low = None

    for swing in swing_lows:

        if previous_low is None:

            swing.label = "START"

        elif swing.price > previous_low:

            swing.label = "HL"

        elif swing.price < previous_low:

            swing.label = "LL"

        else:

            swing.label = "EL"

        previous_low = swing.price


# ==========================================================
# Market Structure
# ==========================================================

def determine_structure(
    swing_highs: List[SwingPoint],
    swing_lows: List[SwingPoint],
) -> str:
    """
    Determine the overall market structure.
    """

    if len(swing_highs) < 2:
        return "Sideways"

    if len(swing_lows) < 2:
        return "Sideways"

    last_high = swing_highs[-1].label
    last_low = swing_lows[-1].label

    # Bullish Trend
    if last_high == "HH" and last_low == "HL":
        return "Bullish"

    # Bearish Trend
    if last_high == "LH" and last_low == "LL":
        return "Bearish"

    # Transition / Consolidation
    return "Sideways"


# ==========================================================
# Main Analysis
# ==========================================================

def analyze_structure(
    swing_highs: List[SwingPoint],
    swing_lows: List[SwingPoint],
) -> Tuple[List[SwingPoint], List[SwingPoint], str]:
    """
    Label all swings and determine the market structure.
    """

    label_highs(swing_highs)
    label_lows(swing_lows)

    structure = determine_structure(
        swing_highs,
        swing_lows,
    )

    return (
        swing_highs,
        swing_lows,
        structure,
    )