"""
smc/confluence.py

BMIE Confluence Engine.

Responsibilities
----------------
- Combine SMC confirmations
- Calculate setup confidence
- Generate BUY / SELL / WAIT decision
- Provide trade reasoning

Author: BMIE Project
"""


from typing import List

from models import (
    TradeDecision,
    MarketStructure,
    BOSEvent,
    CHoCHEvent,
)



class ConfluenceEngine:
    """
    Combines all SMC signals into a trade decision.
    """


    def __init__(
        self,
        market_structure: MarketStructure,
        bos: BOSEvent,
        choch: CHoCHEvent,
        order_blocks: List,
        fair_value_gaps: List,
        liquidity: List,
    ):

        self.market_structure = market_structure

        self.bos = bos

        self.choch = choch

        self.order_blocks = order_blocks

        self.fair_value_gaps = fair_value_gaps

        self.liquidity = liquidity



    # ======================================================
    # Analyze
    # ======================================================

    def analyze(self) -> TradeDecision:
        """
        Generate final trading decision.
        """


        decision = TradeDecision()


        score = 0

        reasons = []



        # ==================================================
        # Market Structure
        # ==================================================

        trend = (
            self.market_structure.trend
        )



        if trend == "Bullish":

            score += 20

            reasons.append(
                "Bullish market structure"
            )


        elif trend == "Bearish":

            score += 20

            reasons.append(
                "Bearish market structure"
            )



        # ==================================================
        # BOS
        # ==================================================

        if self.bos.confirmed:


            if self.bos.direction == "Bullish":

                score += 25

                reasons.append(
                    "Bullish BOS confirmed"
                )


            elif self.bos.direction == "Bearish":

                score += 25

                reasons.append(
                    "Bearish BOS confirmed"
                )



        # ==================================================
        # CHoCH
        # ==================================================

        if self.choch.confirmed:


            score += 15

            reasons.append(
                f"{self.choch.direction} CHoCH confirmed"
            )



        # ==================================================
        # Order Block
        # ==================================================

        if self.order_blocks:

            score += 15

            reasons.append(
                "Order Block available"
            )



        # ==================================================
        # Fair Value Gap
        # ==================================================

        if self.fair_value_gaps:

            score += 15

            reasons.append(
                "Fair Value Gap available"
            )



        # ==================================================
        # Decision
        # ==================================================

        decision.confidence = min(
            score,
            100
        )


        decision.reasons = reasons



        if score >= 70:


            if self.bos.direction == "Bullish":

                decision.signal = "BUY"


            elif self.bos.direction == "Bearish":

                decision.signal = "SELL"



        else:

            decision.signal = "WAIT"



        return decision