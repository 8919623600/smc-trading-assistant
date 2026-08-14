"""
smc/order_blocks.py

BMIE Order Block Engine V2.

Responsibilities
----------------
- Detect Bullish Order Blocks
- Detect Bearish Order Blocks
- Validate freshness
- Calculate OB strength
- Check mitigation
- Check distance from current price

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
    Represents institutional order block.
    """

    direction: str

    high: float

    low: float

    created_at: datetime


    mitigated: bool = False

    broken: bool = False


    strength: int = 0


    source_swing: Optional[SwingPoint] = None


    # New V2 fields

    status: str = "Unknown"

    distance: str = "Unknown"



# ==========================================================
# Order Block Engine
# ==========================================================

class OrderBlockEngine:
    """
    Detects and validates SMC order blocks.
    """



    def __init__(
        self,
        context: AnalysisContext,
    ):

        self.context = context

        self.df = context.df

        print(
            "ORDER BLOCK DF DEBUG:",
            "ROWS=",
            len(self.df),
            "INDEX END=",
            self.df.index[-1],
            "TIME END=",
            self.df.iloc[-1]["time"]
        )

        print(
            "OB ENGINE DATA END:",
            self.df.iloc[-1]["time"],
            "INDEX:",
            self.df.index[-1]
        )

        self.bos = context.bos

        self.swing_highs = context.swing_highs

        self.swing_lows = context.swing_lows



    # ======================================================
    # Distance Validation
    # ======================================================

    def check_distance(
        self,
        block: OrderBlock,
    ):


        current_price = float(
            self.df.iloc[-1]["close"]
        )


        midpoint = (

            block.high

            +
            block.low

        ) / 2



        distance = abs(

            current_price

            -
            midpoint

        )


        # percentage distance

        percent = (

            distance

            /
            current_price

        ) * 100



        if percent <= 0.5:

            block.distance = "Valid"


        elif percent <= 2:

            block.distance = "Acceptable"


        else:

            block.distance = "Far"



        return block



    # ======================================================
    # Strength Calculation
    # ======================================================

    def calculate_strength(
        self,
        block: OrderBlock,
    ):


        score = 0



        # BOS confirmation

        if self.bos.confirmed:

            score += 40



        # Freshness

        if not block.mitigated:

            score += 30



        # Distance

        if block.distance == "Valid":

            score += 20


        elif block.distance == "Acceptable":

            score += 10



        # Cap

        block.strength = min(
            score,
            100
        )


        return block



    # ======================================================
    # Bullish OB
    # ======================================================

    def detect_bullish_order_block(
        self,
    ) -> List[OrderBlock]:


        blocks = []



        if not self.bos.confirmed:

            return blocks


        # Allow bullish reversal OB after bearish BOS
        # when higher timeframe bias is bullish

        if self.bos.direction not in [
            "Bullish",
            "Bearish"
        ]:

            return blocks



        bos_time = self.bos.time

        print(
            "BULLISH OB BOS DEBUG:",
            "bos_time=",
            bos_time,
            "exists=",
            bos_time in self.df.index
        )



        if bos_time not in self.df.index:

            return blocks



        bos_index = self.df.index.get_loc(
            bos_time
        )



        for i in range(

            bos_index - 1,

            max(
                bos_index - 30,
                0
            ),

            -1

        ):


            candle = self.df.iloc[i]


            open_price = float(
                candle["open"]
            )


            close_price = float(
                candle["close"]
            )



            # last bearish candle before BOS

            if close_price < open_price:



                block = OrderBlock(

                    direction="Bullish",

                    high=float(
                        candle["high"]
                    ),

                    low=float(
                        candle["low"]
                    ),

                    created_at=self.df.iloc[i]["time"],

                )



                blocks.append(
                    block
                )


                break



        return blocks



    # ======================================================
    # Bearish OB
    # ======================================================

    def detect_bearish_order_block(
        self,
    ) -> List[OrderBlock]:


        blocks = []



        if not self.bos.confirmed:

            return blocks



        if self.bos.direction not in [
            "Bearish",
            "Bullish"
        ]:

            return blocks



        bos_time = self.bos.time

        print(
            "BEARISH OB BOS DEBUG:",
            "bos_time=",
            bos_time,
            "exists=",
            bos_time in self.df.index
        )



        if bos_time not in self.df.index:

            return blocks



        bos_index = self.df.index.get_loc(
            bos_time
        )



        for i in range(

            bos_index - 1,

            max(
                bos_index - 30,
                0
            ),

            -1

        ):



            candle = self.df.iloc[i]


            open_price = float(
                candle["open"]
            )


            close_price = float(
                candle["close"]
            )



            # last bullish candle before BOS

            if close_price > open_price:



                block = OrderBlock(

                    direction="Bearish",

                    high=float(
                        candle["high"]
                    ),

                    low=float(
                        candle["low"]
                    ),

                    created_at=self.df.iloc[i]["time"],

                )



                blocks.append(
                    block
                )


                break



        return blocks



    # ======================================================
    # Mitigation
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

                block.status = "Mitigated"



            elif (

                block.direction == "Bullish"

                and current_price < block.low

            ):


                block.broken = True

                block.status = "Broken"



            elif (

                block.direction == "Bearish"

                and current_price > block.high

            ):

                # Ignore break if this is the BOS created by this OB
                print(
                    "MITIGATION BOS DEBUG:",
                    "confirmed=",
                    getattr(self.bos, "confirmed", None),
                    "direction=",
                    getattr(self.bos, "direction", None),
                    "bos_time=",
                    getattr(self.bos, "time", None),
                    "block_created=",
                    block.created_at
                )

                if (
                    self.bos
                    and self.bos.confirmed
                    and self.bos.direction == "Bullish"
                    and self.bos.time >= block.created_at
                ):

                    block.broken = False
                    block.status = "Fresh"

                else:

                    block.broken = True
                    block.status = "Broken"



        return blocks



    # ======================================================
    # Public API
    # ======================================================

    def analyze(self):

        blocks = []


        bullish_blocks = self.detect_bullish_order_block()

        print(
            "BULLISH OB FOUND:",
            len(bullish_blocks)
        )


        bearish_blocks = self.detect_bearish_order_block()

        print(
            "BEARISH OB FOUND:",
            len(bearish_blocks)
        )


        blocks.extend(
            bullish_blocks
        )


        blocks.extend(
            bearish_blocks
        )



        blocks = self.check_mitigation(
            blocks
        )



        for block in blocks:


            self.check_distance(
                block
            )


            self.calculate_strength(
                block
            )


            if block.status == "Unknown":


                if block.distance == "Far":

                    block.status = "Far"


                else:

                    block.status = "Fresh"



        return sorted(

            blocks,

            key=lambda x:x.created_at,

        )