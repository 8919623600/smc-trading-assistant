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
    Combines market structure, BOS and CHoCH
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
        # Bullish Structure
        # ==================================================

        if current_trend == "Bullish":

            # Bullish BOS confirms continuation
            if (
                self.bos.confirmed
                and self.bos.direction == "Bullish"
            ):

                state.phase = "Bullish Continuation"
                state.active_event = "BOS"

                state.reason = (
                    "Bullish structure continuation confirmed"
                )

                return state


            # Bearish CHoCH means possible reversal
            if (
                self.choch.confirmed
                and self.choch.direction == "Bearish"
            ):

                state.phase = "Transition"
                state.active_event = "CHoCH"

                state.reason = (
                    "Bearish change of character detected"
                )

                return state


        # ==================================================
        # Bearish Structure
        # ==================================================

        elif current_trend == "Bearish":

            # Bearish BOS confirms continuation
            if (
                self.bos.confirmed
                and self.bos.direction == "Bearish"
            ):

                state.phase = "Bearish Continuation"
                state.active_event = "BOS"

                state.reason = (
                    "Bearish structure continuation confirmed"
                )

                return state


            # Bullish CHoCH means possible reversal
            if (
                self.choch.confirmed
                and self.choch.direction == "Bullish"
            ):

                state.phase = "Transition"
                state.active_event = "CHoCH"

                state.reason = (
                    "Bullish change of character detected"
                )

                return state


        # ==================================================
        # Sideways / Transition Structure
        # ==================================================

        else:

            if self.bos.confirmed:

                if self.bos.direction == "Bullish":

                    state.phase = "Transition"
                    state.active_event = "BOS"

                    state.reason = (
                        "Bullish break inside neutral structure"
                    )

                    return state


                if self.bos.direction == "Bearish":

                    state.phase = "Transition"
                    state.active_event = "BOS"

                    state.reason = (
                        "Bearish break inside neutral structure"
                    )

                    return state


        # ==================================================
        # Default
        # ==================================================

        if current_trend == "Bullish":

            state.phase = "Bullish Continuation"
            state.reason = "Bullish market structure"


        elif current_trend == "Bearish":

            state.phase = "Bearish Continuation"
            state.reason = "Bearish market structure"


        else:

            state.phase = "Range"
            state.reason = "No clear directional structure"


        return state