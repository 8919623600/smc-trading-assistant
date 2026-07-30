"""
smc/confluence.py

BMIE Multi-Timeframe Confluence Engine V3.

Responsibilities
----------------
- Combine multi-timeframe SMC confirmations
- Weight higher timeframe bias
- Calculate confidence
- Generate BUY / SELL / WATCH / WAIT
- Provide reasoning

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


        decision = TradeDecision()


        score = 0

        bullish_score = 0

        bearish_score = 0

        reasons = []



        # ==================================================
        # 1D Bias
        # ==================================================

        if self.context.bias:


            structure = (
                self.context.bias.market_structure
            )


            if structure:


                if structure.trend == "Bullish":

                    score += 25

                    bullish_score += 25

                    reasons.append(
                        "Daily bias bullish"
                    )


                elif structure.trend == "Bearish":

                    score += 25

                    bearish_score += 25

                    reasons.append(
                        "Daily bias bearish"
                    )


                else:

                    score -= 10

                    reasons.append(
                        "Daily bias transition"
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

                    bullish_score += 20

                    reasons.append(
                        "4H structure bullish"
                    )


                elif structure.trend == "Bearish":

                    score += 20

                    bearish_score += 20

                    reasons.append(
                        "4H structure bearish"
                    )


                else:

                    score -= 10

                    reasons.append(
                        "4H structure transition"
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

                    score += 15

                    bullish_score += 15

                    reasons.append(
                        "1H trend bullish"
                    )


                elif structure.trend == "Bearish":

                    score += 15

                    bearish_score += 15

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


                    bullish_score += 15

                    reasons.append(
                        "15M bullish BOS confirmed"
                    )


                else:


                    bearish_score += 15

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


                    bullish_score += 10

                    reasons.append(
                        "5M bullish BOS confirmation"
                    )


                else:


                    bearish_score += 10

                    reasons.append(
                        "5M bearish BOS confirmation"
                    )



            if self.context.entry.choch.confirmed:


                score += 5

                reasons.append(
                    "5M CHoCH confirmation"
                )



        # ==================================================
        # Order Block
        # ==================================================

        if self.context.entry:


            if self.context.entry.order_blocks:


                score += 5

                reasons.append(
                    "Order Block available"
                )



        # ==================================================
        # FVG
        # ==================================================

        if self.context.entry:


            if self.context.entry.fair_value_gaps:


                score += 5

                reasons.append(
                    "Fair Value Gap available"
                )



        # ==================================================
        # Liquidity
        # ==================================================

        if self.context.entry:


            if self.context.entry.liquidity:


                score += 5

                reasons.append(
                    "Liquidity confirmation"
                )



        # ==================================================
        # Normalize
        # ==================================================

        score = max(
            0,
            min(score,100)
        )


        decision.confidence = score


        decision.reasons = reasons



        # ==================================================
        # Signal Classification
        # ==================================================

        if score < 50:


            decision.signal = "WAIT"



        elif score < 70:


            decision.signal = "WATCH"



        elif score < 85:


            if bullish_score > bearish_score:

                decision.signal = "BUY"


            elif bearish_score > bullish_score:

                decision.signal = "SELL"


            else:

                decision.signal = "WATCH"



        else:


            if bullish_score > bearish_score:

                decision.signal = "STRONG BUY"


            elif bearish_score > bullish_score:

                decision.signal = "STRONG SELL"


            else:

                decision.signal = "WATCH"



        return decision