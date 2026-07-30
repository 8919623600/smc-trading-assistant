"""
smc/order_blocks.py

Order Block Engine for BMIE.

Responsibilities
----------------
- Detect Bullish Order Blocks
- Detect Bearish Order Blocks
- Use BOS confirmation
- Return typed OrderBlock objects

Author: BMIE Project
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from models import SwingPoint
from core.analysis_context import AnalysisContext


# ==========================================================
# Order Block Model
# ==========================================================

@dataclass
class OrderBlock:
    """
    Represents an institutional order block.
    """

    direction: str

    high: float

    low: float

    created_at: datetime

    mitigated: bool = False

    broken: bool = False

    strength: int = 0

    source_swing: Optional[SwingPoint] = None



# ==========================================================
# Order Block Engine
# ==========================================================

class OrderBlockEngine:
    """
    Detects Order Blocks using market structure
    and BOS confirmation.
    """


    def __init__(
        self,
        context: AnalysisContext,
    ):

        self.context = context

        self.df = context.df

        self.bos = context.bos

        self.choch = context.choch

        self.swing_highs = context.swing_highs

        self.swing_lows = context.swing_lows



    # ======================================================
    # Bullish Order Block
    # ======================================================

    def detect_bullish_order_block(
        self,
    ) -> List[OrderBlock]:

        blocks = []


        # Need bullish BOS
        if not self.bos.confirmed:
            return blocks


        if self.bos.direction != "Bullish":
            return blocks



        candles = self.df


        bos_time = self.bos.time


        if bos_time not in candles.index:
            return blocks



        bos_index = candles.index.get_loc(
            bos_time
        )


        # Search backwards for last bearish candle

        for i in range(
            bos_index - 1,
            max(bos_index - 20, 0),
            -1
        ):

            candle = candles.iloc[i]


            open_price = float(
                candle["open"]
            )

            close_price = float(
                candle["close"]
            )


            # bearish candle

            if close_price < open_price:

                high = float(
                    candle["high"]
                )

                low = float(
                    candle["low"]
                )


                blocks.append(
                    OrderBlock(
                        direction="Bullish",
                        high=high,
                        low=low,
                        created_at=candles.index[i],
                        strength=1,
                    )
                )


                break


        return blocks



    # ======================================================
    # Bearish Order Block
    # ======================================================

    def detect_bearish_order_block(
        self,
    ) -> List[OrderBlock]:

        blocks = []


        # Need bearish BOS

        if not self.bos.confirmed:
            return blocks


        if self.bos.direction != "Bearish":
            return blocks



        candles = self.df


        bos_time = self.bos.time


        if bos_time not in candles.index:
            return blocks



        bos_index = candles.index.get_loc(
            bos_time
        )


        # Search backwards for last bullish candle

        for i in range(
            bos_index - 1,
            max(bos_index - 20, 0),
            -1
        ):

            candle = candles.iloc[i]


            open_price = float(
                candle["open"]
            )

            close_price = float(
                candle["close"]
            )


            # bullish candle

            if close_price > open_price:

                high = float(
                    candle["high"]
                )

                low = float(
                    candle["low"]
                )


                blocks.append(
                    OrderBlock(
                        direction="Bearish",
                        high=high,
                        low=low,
                        created_at=candles.index[i],
                        strength=1,
                    )
                )


                break


        return blocks



    # ======================================================
    # Mitigation Check
    # ======================================================

    def check_mitigation(
        self,
        blocks: List[OrderBlock],
    ):

        current_price = float(
            self.df.iloc[-1]["close"]
        )


        for block in blocks:

            if (
                block.low
                <= current_price
                <= block.high
            ):

                block.mitigated = True



        return blocks



    # ======================================================
    # Public API
    # ======================================================

    def analyze(
        self,
    ) -> List[OrderBlock]:

        blocks = []


        blocks.extend(
            self.detect_bullish_order_block()
        )


        blocks.extend(
            self.detect_bearish_order_block()
        )


        blocks = self.check_mitigation(
            blocks
        )


        return sorted(
            blocks,
            key=lambda x: x.created_at,
        )