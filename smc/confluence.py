"""
smc/confluence.py

BMIE Multi-Timeframe Confluence Engine V2.

Responsibilities
----------------
- Combine all timeframe confirmations
- Calculate confidence score
- Generate BUY / SELL / WAIT decision
- Provide trade reasoning

Timeframes:
------------
1D  -> Bias
4H  -> Structure
1H  -> Trend
15M -> Setup
5M  -> Entry

Author: BMIE Project
"""


from models import (
    TradeDecision,
    MultiTimeframeContext,
)



class ConfluenceEngine:
    """
    Multi timeframe SMC confluence engine.
    """


    def __init__(
        self,
        context: MultiTimeframeContext,
    ):

        self.context = context



    # ======================================================
    # Analyze
    # ======================================================

    def analyze(self) -> TradeDecision:
        """
        Generate final trade decision.
        """

        decision = TradeDecision()


        score = 0

        reasons = []

        bullish_points = 0

        bearish_points = 0



        # ==================================================
        # 1D Bias
        # ==================================================

        if self.context.bias:

            structure = (
                self.context.bias.market_structure
            )


            if structure:

                if structure.trend == "Bullish":

                    score += 20
                    bullish_points += 20

                    reasons.append(
                        "Daily bias bullish"
                    )


                elif structure.trend == "Bearish":

                    score += 20
                    bearish_points += 20

                    reasons.append(
                        "Daily bias bearish"
                    )



        # ==================================================
        # 4H Structure
        # ==================================================

        if self.context.structure:

            structure = (
                self.context.structure.market_structure
            )


            if structure:

                if structure.trend == "Bullish":

                    score += 20
                    bullish_points += 20

                    reasons.append(
                        "4H structure bullish"
                    )


                elif structure.trend == "Bearish":

                    score += 20
                    bearish_points += 20

                    reasons.append(
                        "4H structure bearish"
                    )



        # ==================================================
        # 1H Trend
        # ==================================================

        if self.context.trend:

            structure = (
                self.context.trend.market_structure
            )


            if structure:

                if structure.trend == "Bullish":

                    score += 20
                    bullish_points += 20

                    reasons.append(
                        "1H trend bullish"
                    )


                elif structure.trend == "Bearish":

                    score += 20
                    bearish_points += 20

                    reasons.append(
                        "1H trend bearish"
                    )



        # ==================================================
        # 15M Setup
        # ==================================================

        if self.context.setup:

            if self.context.setup.bos.confirmed:

                score += 15


                if self.context.setup.bos.direction == "Bullish":

                    bullish_points += 15

                    reasons.append(
                        "15M bullish BOS confirmed"
                    )


                elif self.context.setup.bos.direction == "Bearish":

                    bearish_points += 15

                    reasons.append(
                        "15M bearish BOS confirmed"
                    )



        # ==================================================
        # 5M Entry
        # ==================================================

        if self.context.entry:


            if self.context.entry.bos.confirmed:

                score += 10


                if self.context.entry.bos.direction == "Bullish":

                    bullish_points += 10

                    reasons.append(
                        "5M bullish BOS entry confirmation"
                    )


                elif self.context.entry.bos.direction == "Bearish":

                    bearish_points += 10

                    reasons.append(
                        "5M bearish BOS entry confirmation"
                    )



            if self.context.entry.choch.confirmed:

                score += 5


                reasons.append(
                    "5M CHoCH confirmation"
                )



        # ==================================================
        # Order Block
        # ==================================================

        entry = self.context.entry


        if entry and entry.order_blocks:

            score += 5

            reasons.append(
                "Order Block available"
            )



        # ==================================================
        # FVG
        # ==================================================

        if entry and entry.fair_value_gaps:

            score += 5

            reasons.append(
                "Fair Value Gap available"
            )



        # ==================================================
        # Final Decision
        # ==================================================

        decision.confidence = min(
            score,
            100
        )


        decision.reasons = reasons



        if score < 60:

            decision.signal = "WAIT"


        else:

            if bullish_points > bearish_points:

                decision.signal = "BUY"


            elif bearish_points > bullish_points:

                decision.signal = "SELL"


            else:

                decision.signal = "WAIT"



        return decision