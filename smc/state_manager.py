"""
smc/state_manager.py

Market State Manager for BMIE.

Responsibilities
----------------
- Interpret BOS and CHoCH together
- Resolve conflicting structural signals
- Determine current market phase

Author: BMIE Project
"""

from dataclasses import dataclass

from models import (
    MarketStructure,
    BOSEvent,
    CHoCHEvent,
)


# ==========================================================
# Market State
# ==========================================================

@dataclass
class MarketState:
    """
    Represents the interpreted market condition.
    """

    trend: str = "Sideways"

    phase: str = "Unknown"

    active_event: str = ""

    reason: str = ""


# ==========================================================
# State Manager
# ==========================================================

class MarketStateManager:
    """
    Combines structure, BOS and CHoCH
    into a single market interpretation.
    """

    def __init__(
        self,
        market_structure: MarketStructure,
        bos: BOSEvent,
        choch: CHoCHEvent,
    ):

        self.market_structure = market_structure
        self.bos = bos
        self.choch = choch


    # ======================================================
    # Analyze
    # ======================================================

    def analyze(self) -> MarketState:
        """
        Determine current market phase.
        """

        state = MarketState()

        current_trend = self.market_structure.trend

        state.trend = current_trend


        # ==================================================
        # Newer BOS has priority
        # ==================================================

        if self.bos.confirmed:

            if self.bos.direction == "Bullish":

                state.phase = "Bullish Continuation"

                state.active_event = "BOS"

                state.reason = (
                    "Bullish structure break confirmed"
                )

                return state


            if self.bos.direction == "Bearish":

                state.phase = "Bearish Continuation"

                state.active_event = "BOS"

                state.reason = (
                    "Bearish structure break confirmed"
                )

                return state


        # ==================================================
        # CHoCH means transition
        # ==================================================

        if self.choch.confirmed:

            state.phase = "Transition"

            state.active_event = "CHoCH"

            state.reason = (
                "Possible market direction change"
            )

            return state


        # ==================================================
        # Existing trend
        # ==================================================

        if current_trend == "Bullish":

            state.phase = "Bullish Continuation"

            state.reason = (
                "Bullish market structure"
            )


        elif current_trend == "Bearish":

            state.phase = "Bearish Continuation"

            state.reason = (
                "Bearish market structure"
            )


        else:

            state.phase = "Range"

            state.reason = (
                "No clear directional structure"
            )


        return state