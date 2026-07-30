"""
smc/market_structure.py

Market Structure Engine for BMIE.

This module determines the current market phase
from major swing highs and lows.

Author: BMIE Project
"""

from dataclasses import dataclass
from typing import List, Optional

from models import SwingPoint


# ==========================================================
# Market States
# ==========================================================

BULLISH_CONTINUATION = "Bullish Continuation"

BEARISH_CONTINUATION = "Bearish Continuation"

TRANSITION = "Transition"

RANGE = "Range"


# ==========================================================
# Market Structure State
# ==========================================================

@dataclass
class MarketStructureState:
    """
    Represents the current market structure.
    """

    trend: str = "Sideways"

    state: str = TRANSITION

    last_high: Optional[SwingPoint] = None

    last_low: Optional[SwingPoint] = None


# ==========================================================
# Market Structure Engine
# ==========================================================

class MarketStructureEngine:
    """
    Builds market structure from major swing points.
    """

    def __init__(
        self,
        swing_highs: List[SwingPoint],
        swing_lows: List[SwingPoint],
    ):

        self.swing_highs = swing_highs
        self.swing_lows = swing_lows


    # ======================================================
    # Analyze
    # ======================================================

    def analyze(self) -> MarketStructureState:
        """
        Determine current market structure state.
        """

        state = MarketStructureState()

        if len(self.swing_highs) < 2:
            return state

        if len(self.swing_lows) < 2:
            return state


        # Latest confirmed swings

        last_high = self.swing_highs[-1]
        previous_high = self.swing_highs[-2]

        last_low = self.swing_lows[-1]
        previous_low = self.swing_lows[-2]


        state.last_high = last_high
        state.last_low = last_low


        # ==================================================
        # Bullish Structure
        # ==================================================

        if (
            last_high.label == "HH"
            and last_low.label == "HL"
        ):

            state.trend = "Bullish"
            state.state = BULLISH_CONTINUATION

            return state


        # ==================================================
        # Bearish Structure
        # ==================================================

        if (
            last_high.label == "LH"
            and last_low.label == "LL"
        ):

            state.trend = "Bearish"
            state.state = BEARISH_CONTINUATION

            return state


        # ==================================================
        # Transition
        # ==================================================

        if (
            previous_high.label in ["HH", "LH"]
            and previous_low.label in ["HL", "LL"]
        ):

            state.trend = "Sideways"
            state.state = TRANSITION

            return state


        # ==================================================
        # Range
        # ==================================================

        state.trend = "Sideways"
        state.state = RANGE

        return state