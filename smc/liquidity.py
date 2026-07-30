"""
smc/liquidity.py

Liquidity detection module for BMIE.

Responsibilities
----------------
- Detect Equal Highs (EQH)
- Detect Equal Lows (EQL)
- Identify Buy-side Liquidity
- Identify Sell-side Liquidity

Author: BMIE Project
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List

from models import SwingPoint


# ==========================================================
# Liquidity Zone
# ==========================================================

@dataclass
class LiquidityZone:
    """
    Represents a liquidity pool formed by equal highs
    or equal lows.
    """

    side: str                 # Buy-side / Sell-side
    level: float
    start_time: datetime
    end_time: datetime

    swept: bool = False

    swing_points: List[SwingPoint] = None


# ==========================================================
# Liquidity Engine
# ==========================================================

class LiquidityEngine:
    """
    Detects liquidity zones from major swings.
    """

    def __init__(
        self,
        swing_highs: List[SwingPoint],
        swing_lows: List[SwingPoint],
        tolerance: float = 0.20,
    ):

        self.swing_highs = swing_highs
        self.swing_lows = swing_lows
        self.tolerance = tolerance

    # ======================================================

    def detect_equal_highs(self) -> List[LiquidityZone]:
        """
        Detect Equal Highs (Buy-side Liquidity).
        """

        zones = []

        if len(self.swing_highs) < 2:
            return zones

        for i in range(len(self.swing_highs) - 1):

            first = self.swing_highs[i]
            second = self.swing_highs[i + 1]

            if abs(first.price - second.price) <= self.tolerance:

                zones.append(
                    LiquidityZone(
                        side="Buy-side",
                        level=(first.price + second.price) / 2,
                        start_time=first.time,
                        end_time=second.time,
                        swing_points=[first, second],
                    )
                )

        return zones

    # ======================================================

    def detect_equal_lows(self) -> List[LiquidityZone]:
        """
        Detect Equal Lows (Sell-side Liquidity).
        """

        zones = []

        if len(self.swing_lows) < 2:
            return zones

        for i in range(len(self.swing_lows) - 1):

            first = self.swing_lows[i]
            second = self.swing_lows[i + 1]

            if abs(first.price - second.price) <= self.tolerance:

                zones.append(
                    LiquidityZone(
                        side="Sell-side",
                        level=(first.price + second.price) / 2,
                        start_time=first.time,
                        end_time=second.time,
                        swing_points=[first, second],
                    )
                )

        return zones

    # ======================================================

    def analyze(self) -> List[LiquidityZone]:
        """
        Run complete liquidity analysis.
        """

        liquidity = []

        liquidity.extend(self.detect_equal_highs())
        liquidity.extend(self.detect_equal_lows())

        return liquidity