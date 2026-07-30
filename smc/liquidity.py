"""
smc/liquidity.py

Liquidity Engine V4 for BMIE.

Responsibilities
----------------
- Detect Equal Highs (EQH)
- Detect Equal Lows (EQL)
- Identify Buy-side Liquidity
- Identify Sell-side Liquidity
- Detect Liquidity Sweeps
- Validate sweep quality
- Track sweep distance
- Rank liquidity zones
- Select best institutional liquidity

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


    # Sweep status

    swept: bool = False

    sweep_valid: bool = False



    # Sweep details

    sweep_time: Optional[datetime] = None

    sweep_price: Optional[float] = None

    sweep_distance: Optional[float] = None



    # Ranking details

    distance_from_price: Optional[float] = None

    strength: int = 0



    swing_points: List[SwingPoint] = field(
        default_factory=list
    )




# ==========================================================
# Liquidity Engine
# ==========================================================

class LiquidityEngine:
    """
    Detects liquidity pools and validates sweeps.
    """



    def __init__(
        self,
        swing_highs: List[SwingPoint],
        swing_lows: List[SwingPoint],
        df=None,
        tolerance: float = 1.50,
        max_sweep_distance: float = 30.0,
    ):

        self.swing_highs = swing_highs

        self.swing_lows = swing_lows

        self.df = df

        self.tolerance = tolerance

        self.max_sweep_distance = max_sweep_distance




    # ======================================================
    # Equal Highs
    # ======================================================

    def detect_equal_highs(self):


        zones = []


        if len(self.swing_highs) < 2:

            return zones



        for i in range(

            len(self.swing_highs) - 1

        ):


            first = self.swing_highs[i]

            second = self.swing_highs[i + 1]



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

            len(self.swing_lows) - 1

        ):


            first = self.swing_lows[i]

            second = self.swing_lows[i + 1]



            if abs(

                first.price - second.price

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
    # Sweep Detection + Validation
    # ======================================================

    def detect_sweeps(
        self,
        zones: List[LiquidityZone],
    ):


        if self.df is None:

            return zones



        for zone in zones:



            for index, candle in self.df.iterrows():


                high = float(
                    candle["high"]
                )


                low = float(
                    candle["low"]
                )



                # ==========================================
                # Buy-side liquidity sweep
                # ==========================================

                if zone.side == "Buy-side":


                    if high > zone.level:



                        distance = (

                            high

                            -

                            zone.level

                        )


                        zone.swept = True


                        zone.sweep_time = index


                        zone.sweep_price = high


                        zone.sweep_distance = distance



                        if distance <= self.max_sweep_distance:


                            zone.sweep_valid = True



                        break




                # ==========================================
                # Sell-side liquidity sweep
                # ==========================================

                if zone.side == "Sell-side":


                    if low < zone.level:



                        distance = (

                            zone.level

                            -

                            low

                        )


                        zone.swept = True


                        zone.sweep_time = index


                        zone.sweep_price = low


                        zone.sweep_distance = distance



                        if distance <= self.max_sweep_distance:


                            zone.sweep_valid = True



                        break



        return zones





    # ======================================================
    # Liquidity Ranking
    # ======================================================

    def rank_liquidity(
        self,
        zones: List[LiquidityZone],
        current_price: float,
        direction: str,
    ):


        candidates = []



        for zone in zones:



            # Only swept liquidity

            if not zone.swept:

                continue



            # Only valid sweep

            if not zone.sweep_valid:

                continue



            # Bullish setup
            # Need sell-side liquidity

            if direction == "Bullish":


                if zone.side != "Sell-side":

                    continue



            # Bearish setup
            # Need buy-side liquidity

            if direction == "Bearish":


                if zone.side != "Buy-side":

                    continue



            distance = abs(

                current_price

                -

                zone.level

            )



            zone.distance_from_price = distance



            strength = 0



            # Valid sweep weight

            if zone.sweep_valid:


                strength += 50



            # Sweep quality

            if zone.sweep_distance is not None:


                if zone.sweep_distance < 5:


                    strength += 30


                elif zone.sweep_distance < 15:


                    strength += 20


                else:


                    strength += 10



            # Recency bonus

            strength += 20



            zone.strength = strength



            candidates.append(zone)




        if not candidates:

            return None




        # Strongest + nearest liquidity

        candidates.sort(

            key=lambda x:

            (

                -x.strength,

                x.distance_from_price

            )

        )



        return candidates[0]





    # ======================================================
    # Get Best Liquidity
    # ======================================================

    def get_best_liquidity(
        self,
        zones,
        current_price,
        direction,
    ):


        return self.rank_liquidity(

            zones,

            current_price,

            direction

        )





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