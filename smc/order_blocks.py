"""
smc/order_blocks.py

Order Block Engine for BMIE.

Responsibilities
----------------
- Detect Bullish Order Blocks
- Detect Bearish Order Blocks
- Return typed OrderBlock objects

Author: BMIE Project
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List

from models import SwingPoint


# ==========================================================
# Order Block
# ==========================================================

@dataclass
class OrderBlock:
    """
    Represents an institutional order block.
    """

    direction: str           # Bullish / Bearish

    high: float

    low: float

    created_at: datetime

    mitigated: bool = False

    broken: bool = False

    strength: int = 0

    source_swing: SwingPoint = None


# ==========================================================
# Order Block Engine
# ==========================================================

class OrderBlockEngine:
    """
    Detects Order Blocks from major swing points.
    """

    def __init__(
        self,
        swing_highs: List[SwingPoint],
        swing_lows: List[SwingPoint],
    ):

        self.swing_highs = swing_highs
        self.swing_lows = swing_lows

    # ======================================================

    def detect_bullish_order_blocks(self) -> List[OrderBlock]:
        """
        Build Bullish Order Blocks from major swing lows.
        """

        blocks = []

        for swing in self.swing_lows:

            if swing.label != "HL":
                continue

            blocks.append(
                OrderBlock(
                    direction="Bullish",
                    high=swing.price,
                    low=swing.price,
                    created_at=swing.time,
                    strength=swing.strength,
                    source_swing=swing,
                )
            )

        return blocks

    # ======================================================

    def detect_bearish_order_blocks(self) -> List[OrderBlock]:
        """
        Build Bearish Order Blocks from major swing highs.
        """

        blocks = []

        for swing in self.swing_highs:

            if swing.label != "LH":
                continue

            blocks.append(
                OrderBlock(
                    direction="Bearish",
                    high=swing.price,
                    low=swing.price,
                    created_at=swing.time,
                    strength=swing.strength,
                    source_swing=swing,
                )
            )

        return blocks

    # ======================================================

    def analyze(self) -> List[OrderBlock]:
        """
        Run complete Order Block analysis.
        """

        blocks = []

        blocks.extend(self.detect_bullish_order_blocks())
        blocks.extend(self.detect_bearish_order_blocks())

        return sorted(
            blocks,
            key=lambda block: block.created_at,
        )