"""
smc/fvg.py

Fair Value Gap (FVG) Engine V2 for BMIE.

Responsibilities
----------------
- Detect Bullish Fair Value Gaps
- Detect Bearish Fair Value Gaps
- Track FVG mitigation
- Return clean FVG objects
- Remove invalid historical gaps

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
    Represents market imbalance.
    """

    direction: str

    high: float

    low: float

    created_at: datetime

    filled: bool = False

    strength: int = 0



# ==========================================================
# FVG Engine
# ==========================================================

class FVGEngine:


    def __init__(
        self,
        context: AnalysisContext,
    ):

        self.context = context

        self.df = context.df



    # ======================================================
    # Bullish FVG
    # ======================================================

    def detect_bullish_fvg(self):


        gaps = []


        df = self.df



        for i in range(
            2,
            len(df)
        ):


            candle1 = df.iloc[i-2]

            candle3 = df.iloc[i]



            first_high = float(
                candle1["high"]
            )


            third_low = float(
                candle3["low"]
            )



            if third_low > first_high:


                gap = FairValueGap(

                    direction="Bullish",

                    low=first_high,

                    high=third_low,

                    created_at=df.index[i],

                    strength=1

                )


                gaps.append(gap)



        return gaps



    # ======================================================
    # Bearish FVG
    # ======================================================

    def detect_bearish_fvg(self):


        gaps = []


        df = self.df



        for i in range(
            2,
            len(df)
        ):


            candle1 = df.iloc[i-2]

            candle3 = df.iloc[i]



            first_low = float(
                candle1["low"]
            )


            third_high = float(
                candle3["high"]
            )



            if third_high < first_low:


                gap = FairValueGap(

                    direction="Bearish",

                    low=third_high,

                    high=first_low,

                    created_at=df.index[i],

                    strength=1

                )


                gaps.append(gap)



        return gaps



    # ======================================================
    # Mitigation Check
    # ======================================================

    def check_filled(
        self,
        gaps: List[FairValueGap],
    ):


        df = self.df



        for gap in gaps:


            created_index = df.index.get_loc(
                gap.created_at
            )



            future_candles = df.iloc[
                created_index + 1 :
            ]



            for _, candle in future_candles.iterrows():


                high = float(
                    candle["high"]
                )


                low = float(
                    candle["low"]
                )



                # Price returned into FVG

                if (

                    low <= gap.high

                    and

                    high >= gap.low

                ):


                    gap.filled = True


                    break



        return gaps



    # ======================================================
    # Remove Old Filled Gaps
    # ======================================================

    def clean_gaps(
        self,
        gaps,
    ):


        return sorted(

            gaps,

            key=lambda x:x.created_at,

            reverse=True

        )[:5]



    # ======================================================
    # Public API
    # ======================================================

    def analyze(self):


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



        gaps = self.clean_gaps(

            gaps

        )



        return sorted(

            gaps,

            key=lambda x:x.created_at

        )