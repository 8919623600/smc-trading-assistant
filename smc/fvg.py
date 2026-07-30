"""
smc/fvg.py

Fair Value Gap (FVG) Engine for BMIE.

Responsibilities
----------------
- Detect Bullish Fair Value Gaps
- Detect Bearish Fair Value Gaps
- Track filled gaps
- Return typed FVG objects

Author: BMIE Project
"""


from dataclasses import dataclass
from datetime import datetime
from typing import List


from core.analysis_context import AnalysisContext



# ==========================================================
# Fair Value Gap Model
# ==========================================================

@dataclass
class FairValueGap:
    """
    Represents a market imbalance.
    """

    direction: str       # Bullish / Bearish

    high: float

    low: float

    created_at: datetime

    filled: bool = False

    strength: int = 0



# ==========================================================
# FVG Engine
# ==========================================================

class FVGEngine:
    """
    Detects Fair Value Gaps from candle imbalance.
    """


    def __init__(
        self,
        context: AnalysisContext,
    ):

        self.context = context

        self.df = context.df



    # ======================================================
    # Bullish FVG
    # ======================================================

    def detect_bullish_fvg(
        self,
    ) -> List[FairValueGap]:

        gaps = []


        df = self.df


        for i in range(
            2,
            len(df)
        ):

            candle1 = df.iloc[i - 2]

            candle3 = df.iloc[i]


            candle1_high = float(
                candle1["high"]
            )

            candle3_low = float(
                candle3["low"]
            )


            # Bullish imbalance

            if candle3_low > candle1_high:


                gaps.append(
                    FairValueGap(

                        direction="Bullish",

                        high=candle3_low,

                        low=candle1_high,

                        created_at=df.index[i],

                        strength=1,
                    )
                )


        return gaps



    # ======================================================
    # Bearish FVG
    # ======================================================

    def detect_bearish_fvg(
        self,
    ) -> List[FairValueGap]:

        gaps = []


        df = self.df


        for i in range(
            2,
            len(df)
        ):

            candle1 = df.iloc[i - 2]

            candle3 = df.iloc[i]


            candle1_low = float(
                candle1["low"]
            )

            candle3_high = float(
                candle3["high"]
            )


            # Bearish imbalance

            if candle3_high < candle1_low:


                gaps.append(
                    FairValueGap(

                        direction="Bearish",

                        high=candle1_low,

                        low=candle3_high,

                        created_at=df.index[i],

                        strength=1,
                    )
                )


        return gaps



    # ======================================================
    # Filled Check
    # ======================================================

    def check_filled(
        self,
        gaps: List[FairValueGap],
    ):

        current_price = float(
            self.df.iloc[-1]["close"]
        )


        for gap in gaps:

            if (
                gap.low
                <= current_price
                <= gap.high
            ):

                gap.filled = True


        return gaps



    # ======================================================
    # Public API
    # ======================================================

    def analyze(
        self,
    ) -> List[FairValueGap]:


        gaps = []


        gaps.extend(
            self.detect_bullish_fvg()
        )


        gaps.extend(
            self.detect_bearish_fvg()
        )


        gaps = self.check_filled(
            gaps
        )


        return sorted(
            gaps,
            key=lambda x: x.created_at,
        )