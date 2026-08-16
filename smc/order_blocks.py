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


            # Find last bearish candle before bullish displacement

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


                # bearish candle

                if close_price < open_price:


                    bullish_move = False


                    # Check bullish displacement after this candle

                    for j in range(
                        i + 1,
                        bos_index + 1
                    ):

                        c = self.df.iloc[j]


                        if float(c["close"]) > close_price:

                            bullish_move = True
                            break


                    if bullish_move:

                        origin_index = i
                        break



            if origin_index is None:

                return blocks



            print(
                "BULLISH OB ORIGIN DEBUG:",
                self.df.iloc[origin_index]["time"],
                "HIGH=",
                self.df.iloc[origin_index]["high"],
                "LOW=",
                self.df.iloc[origin_index]["low"]
            )



            block = OrderBlock(

                direction="Bullish",

                high=float(
                    self.df.iloc[bos_index]["high"]
                ),

                low=float(
                    self.df.iloc[origin_index]["low"]
                ),

                created_at=self.df.iloc[
                    origin_index
                ]["time"]

            )


            blocks.append(block)


            return blocks


    # ======================================================
    # Bearish OB
    # ======================================================

    def detect_bearish_order_block(self):

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


        # Find true bearish OB origin
        # Last bullish candle before strong bearish displacement

        candidate_index = None
        candidate_high = 0
        
        for i in range(
            bos_index - 1,
            max(
                bos_index - 50,
                1
            ),
            -1
        ):

            candle = self.df.iloc[i]

            open_price = float(candle["open"])
            close_price = float(candle["close"])


            # Origin must be bullish candle

            # bullish candle candidate

            if close_price <= open_price:
                continue


            # keep the highest bullish candle
            # before bearish displacement

            if float(candle["high"]) > candidate_high:

                candidate_high = float(candle["high"])
                candidate_index = i


            # Check if this bullish candle is the beginning of the move
            # Ignore bullish candles that are inside previous bullish sequence

            if i > 1:

                previous = self.df.iloc[i-1]

                prev_open = float(previous["open"])
                prev_close = float(previous["close"])


                if prev_close > prev_open:
                    continue

            # reject bullish candles that appear after bearish displacement started

            future_bearish = False

            for k in range(i + 1, bos_index + 1):

                k_open = float(self.df.iloc[k]["open"])
                k_close = float(self.df.iloc[k]["close"])

                if k_close < k_open:
                    future_bearish = True
                    break


            if not future_bearish:
                continue

            print(
                "BULLISH CANDIDATE:",
                self.df.iloc[i]["time"],
                "HIGH=",
                self.df.iloc[i]["high"],
                "LOW=",
                self.df.iloc[i]["low"]
            )



            bearish_displacement = False


            displacement_low = float(
                self.df.iloc[bos_index]["low"]
            )


            # Find first bearish displacement candle after origin

            for j in range(
                i + 1,
                bos_index + 1
            ):

                next_candle = self.df.iloc[j]

                next_open = float(next_candle["open"])
                next_close = float(next_candle["close"])
                next_low = float(next_candle["low"])


                # strong bearish candle

                if (
                    next_close < next_open
                    and next_low <= displacement_low
                ):

                    candle_range = (
                        float(next_candle["high"])
                        -
                        float(next_candle["low"])
                    )


                    body = abs(
                        next_open -
                        next_close
                    )


                    # displacement confirmation

                    if body >= candle_range * 0.5:

                        bearish_displacement = True
                        break

            print(
                "PREVIOUS CANDLES DEBUG"
            )

            print(
                self.df.iloc[
                    bos_index-10:
                    bos_index
                ][
                    [
                        "time",
                        "open",
                        "high",
                        "low",
                        "close"
                    ]
                ]
            )


            if bearish_displacement:

                if candidate_index is None:
                   return blocks

                if self.context.timeframe == "5m":

                    origin_index = i

                else:

                    origin_index = candidate_index

                break


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
            bos_index
        ]

        print(
            "ZONE DEBUG",
            zone[["time","open","high","low","close"]].to_string()
        )


        block = OrderBlock(



            direction="Bearish",

            high=float(
                zone["high"].max()
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

