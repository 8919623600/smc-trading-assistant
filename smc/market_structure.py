"""
smc/market_structure.py

Market Structure Engine for BMIE.

This module is responsible for understanding the current
market structure from major swing highs and lows.

Author: BMIE Project
"""

from dataclasses import dataclass
from typing import List, Optional

from models import SwingPoint


# ==========================================================
# Market Structure State
# ==========================================================

@dataclass
class MarketStructureState:
    """
    Represents the current market structure.
    """

    trend: str = "Sideways"

    state: str = "Unknown"

    last_high: Optional[SwingPoint] = None

    last_low: Optional[SwingPoint] = None


# ==========================================================
# Market Structure Engine
# ==========================================================

class MarketStructureEngine:
    """
    Builds the current market structure from major swings.
    """

    def __init__(
        self,
        swing_highs: List[SwingPoint],
        swing_lows: List[SwingPoint],
    ):

        self.swing_highs = swing_highs
        self.swing_lows = swing_lows

    # ======================================================

    def analyze(self) -> MarketStructureState:
        """
        Analyze market structure.

        Returns
        -------
        MarketStructureState
        """

        state = MarketStructureState()

        if len(self.swing_highs) < 2:
            return state

        if len(self.swing_lows) < 2:
            return state

        last_high = self.swing_highs[-1]
        last_low = self.swing_lows[-1]

        state.last_high = last_high
        state.last_low = last_low

        # --------------------------------------------------

        if last_high.label == "HH" and last_low.label == "HL":

            state.trend = "Bullish"
            state.state = "Continuation"

        elif last_high.label == "LH" and last_low.label == "LL":

            state.trend = "Bearish"
            state.state = "Continuation"

        else:

            state.trend = "Sideways"
            state.state = "Transition"

        return state