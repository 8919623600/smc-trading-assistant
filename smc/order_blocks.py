"""
smc/order_blocks.py

BMIE Order Block Engine V2.
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

    direction: str

    high: float

    low: float

    created_at: datetime

    mitigated: bool = False

    broken: bool = False

    strength: int = 0

    source_swing: Optional[SwingPoint] = None

    status: str = "Unknown"

    distance: str = "Unknown"



# ==========================================================
# Order Block Engine
# ==========================================================

class OrderBlockEngine:


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
            block.high +
            block.low
        ) / 2


        distance = abs(
            current_price -
            midpoint
        )


        percent = (
            distance /
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


        if self.bos.confirmed:

            score += 40


        if not block.mitigated:

            score += 30


        if block.distance == "Valid":

            score += 20

        elif block.distance == "Acceptable":

            score += 10



        block.strength = min(
            score,
            100
        )


        return block



    # ======================================================
    # Bullish OB
    # ======================================================

    def detect_bullish_order_block(self):

        blocks = []


        if not self.bos.confirmed:

            return blocks


        if self.bos.direction != "Bullish":

            return blocks



        bos_time = self.bos.time


        time_matches = self.df.index[
            self.df["time"] == bos_time
        ]


        if len(time_matches) == 0:

            return blocks



        bos_index = time_matches[0]


        origin_index = None



                # Find bearish OB origin
                # Last bullish candle before bearish displacement

                for i in range(
                    bos_index - 1,
                    max(
                        bos_index - 50,
                        1
                    ),
                    -1
                ):

                    candle = self.df.iloc[i]


                    close_price = float(
                        candle["close"]
                    )

                    open_price = float(
                        candle["open"]
                    )


                    # bullish candle only

                    if close_price > open_price:


                        bearish_move = False


                        # Check if bearish displacement starts after this candle

                        for j in range(
                            i + 1,
                            bos_index + 1
                        ):

                            c = self.df.iloc[j]


                            if float(c["close"]) < close_price:

                                bearish_move = True
                                break


                        if bearish_move:

                            origin_index = i
                            break



                if origin_index is None:

                    return blocks



        blocks.append(block)


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


        if self.bos.direction != "Bearish":

            return blocks



        bos_time = self.bos.time


        time_matches = self.df.index[
            self.df["time"] == bos_time
        ]


        if len(time_matches) == 0:

            return blocks



        bos_index = time_matches[0]


        origin_index = None



        # Find bearish displacement start
        for i in range(
            bos_index - 1,
            max(
                bos_index - 50,
                1
            ),
            -1
        ):


            candle = self.df.iloc[i]


            close_price = float(
                candle["close"]
            )

            open_price = float(
                candle["open"]
            )


            next_candle = self.df.iloc[i+1]


            next_close = float(
                next_candle["close"]
            )



            # Find bullish origin before bearish displacement
            # Keep searching until displacement start is found

            if close_price > open_price:

                next_candle = self.df.iloc[i + 1]

                next_close = float(
                    next_candle["close"]
                )

                if next_close < close_price:

                    # Last bullish candle before bearish displacement
                    # is the bearish order block origin

                    origin_index = i
                    break



        if origin_index is None:

            return blocks



        print(
            "BEARISH OB ORIGIN DEBUG:",
            self.df.iloc[origin_index]["time"],
            "HIGH=",
            self.df.iloc[origin_index]["high"],
            "LOW=",
            self.df.iloc[origin_index]["low"]
        )



        zone = self.df.iloc[
            origin_index:
            bos_index + 1
        ]

        print(
            "BEARISH OB FINAL DEBUG:",
            "origin=",
            self.df.iloc[origin_index]["time"],
            "origin_high=",
            self.df.iloc[origin_index]["high"],
            "bos_time=",
            self.df.iloc[bos_index]["time"],
            "bos_low=",
            self.df.iloc[bos_index]["low"]
        )



        block = OrderBlock(

            direction="Bearish",

            # Bearish OB:
            # high = origin candle high
            # low  = BOS candle low

            high=float(
                self.df.iloc[origin_index]["high"]
            ),

            low=float(
                self.df.iloc[bos_index]["low"]
            ),

            created_at=self.df.iloc[
                origin_index
            ]["time"]

        )



        blocks.append(block)


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


                print(
                    "MITIGATION BOS DEBUG:",
                    "confirmed=",
                    getattr(
                        self.bos,
                        "confirmed",
                        None
                    ),

                    "direction=",
                    getattr(
                        self.bos,
                        "direction",
                        None
                    ),

                    "bos_time=",
                    getattr(
                        self.bos,
                        "time",
                        None
                    ),

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



        bullish_blocks = (
            self.detect_bullish_order_block()
        )



        print(
            "BULLISH OB FOUND:",
            len(bullish_blocks)
        )



        bearish_blocks = (
            self.detect_bearish_order_block()
        )



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

            key=lambda x: x.created_at

        )

