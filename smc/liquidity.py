"""
smc/liquidity.py

Liquidity Engine V2 for BMIE.

Responsibilities
----------------
- Detect Equal Highs (EQH)
- Detect Equal Lows (EQL)
- Identify Buy-side Liquidity
- Identify Sell-side Liquidity
- Detect Liquidity Sweeps
- Track swept liquidity

Author: BMIE Project
"""


from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from models import SwingPoint



# ==========================================================
# Liquidity Zone
# ==========================================================

@dataclass
class LiquidityZone:
    """
    Represents institutional liquidity.
    """

    side: str

    level: float

    start_time: datetime

    end_time: datetime


    swept: bool = False


    sweep_time: Optional[datetime] = None


    sweep_price: Optional[float] = None


    swing_points: List[SwingPoint] = field(
        default_factory=list
    )



# ==========================================================
# Liquidity Engine
# ==========================================================

class LiquidityEngine:
    """
    Detects liquidity pools and sweeps.
    """



    def __init__(
        self,
        swing_highs: List[SwingPoint],
        swing_lows: List[SwingPoint],
        df=None,
        tolerance: float = 0.20,
    ):

        self.swing_highs = swing_highs

        self.swing_lows = swing_lows

        self.df = df

        self.tolerance = tolerance



    # ======================================================
    # Equal Highs
    # ======================================================

    def detect_equal_highs(self):


        zones = []


        if len(self.swing_highs) < 2:

            return zones



        for i in range(
            len(self.swing_highs)-1
        ):


            first = self.swing_highs[i]

            second = self.swing_highs[i+1]



            if abs(
                first.price - second.price
            ) <= self.tolerance:



                zones.append(

                    LiquidityZone(

                        side="Buy-side",

                        level=(

                            first.price

                            +

                            second.price

                        ) / 2,


                        start_time=first.time,


                        end_time=second.time,


                        swing_points=[

                            first,

                            second

                        ]

                    )

                )



        return zones



    # ======================================================
    # Equal Lows
    # ======================================================

    def detect_equal_lows(self):


        zones = []



        if len(self.swing_lows) < 2:

            return zones



        for i in range(

            len(self.swing_lows)-1

        ):


            first = self.swing_lows[i]

            second = self.swing_lows[i+1]



            if abs(

                first.price-second.price

            ) <= self.tolerance:



                zones.append(

                    LiquidityZone(

                        side="Sell-side",


                        level=(

                            first.price

                            +

                            second.price

                        ) / 2,


                        start_time=first.time,


                        end_time=second.time,


                        swing_points=[

                            first,

                            second

                        ]

                    )

                )



        return zones



    # ======================================================
    # Sweep Detection
    # ======================================================

    def detect_sweeps(
        self,
        zones: List[LiquidityZone],
    ):


        if self.df is None:

            return zones



        for zone in zones:



            candles = self.df



            for index, candle in candles.iterrows():



                high = float(
                    candle["high"]
                )


                low = float(
                    candle["low"]
                )



                # Buy-side liquidity sweep

                if (

                    zone.side == "Buy-side"

                    and

                    high > zone.level

                ):


                    zone.swept = True


                    zone.sweep_time = index


                    zone.sweep_price = high


                    break



                # Sell-side liquidity sweep

                if (

                    zone.side == "Sell-side"

                    and

                    low < zone.level

                ):


                    zone.swept = True


                    zone.sweep_time = index


                    zone.sweep_price = low


                    break



        return zones



    # ======================================================
    # Public API
    # ======================================================

    def analyze(self):


        liquidity = []



        liquidity.extend(

            self.detect_equal_highs()

        )



        liquidity.extend(

            self.detect_equal_lows()

        )



        liquidity = self.detect_sweeps(

            liquidity

        )



        return liquidity