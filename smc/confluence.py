"""
smc/confluence.py

BMIE Multi-Timeframe Confluence Engine.

Responsibilities
----------------
- Combine multi-timeframe SMC confirmations
- Weight HTF and LTF signals
- Validate FVG
- Validate liquidity sweep quality
- Calculate setup confidence
- Generate BUY / SELL / WAIT decision
- Provide trade reasoning

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
    # Fresh FVG Check
    # ======================================================

    def get_fresh_fvg(self):


        if not self.context.entry:

            return []


        if not self.context.entry.fair_value_gaps:

            return []



        return [

            fvg

            for fvg in self.context.entry.fair_value_gaps

            if not fvg.filled

        ]



    # ======================================================
    # FVG Direction Validation
    # ======================================================

    def validate_fvg_direction(
        self,
        direction,
        fvg_list,
    ):


        valid = []

        ignored = []



        for fvg in fvg_list:


            fvg_direction = str(
                fvg.direction
            ).lower()



            if direction == "Bullish":


                if fvg_direction == "bullish":

                    valid.append(fvg)


                else:

                    ignored.append(fvg)



            elif direction == "Bearish":


                if fvg_direction == "bearish":

                    valid.append(fvg)


                else:

                    ignored.append(fvg)



        return valid, ignored



    # ======================================================
    # Liquidity Validation
    # ======================================================

    def validate_liquidity(
        self,
        direction,
    ):


        liquidity = []



        if self.context.entry:


            liquidity = (

                self.context.entry.liquidity

                or []

            )



        if not liquidity:


            return {

                "valid": False,

                "reason":

                    "No liquidity confirmation"

            }



        invalid_sweep = False



        for zone in liquidity:


            print(

                "LIQUIDITY DEBUG:",

                zone.side,

                zone.level,

                zone.swept,

                getattr(
                    zone,
                    "sweep_valid",
                    None
                ),

                getattr(
                    zone,
                    "sweep_distance",
                    None
                )

            )



            # ==============================================
            # Bullish Setup
            # Need Sell-side Liquidity Sweep
            # ==============================================

            if direction == "Bullish":


                if (

                    zone.side == "Sell-side"

                    and

                    zone.swept

                ):


                    if getattr(

                        zone,

                        "sweep_valid",

                        False

                    ):


                        return {

                            "valid": True,

                            "reason":

                                "Sell-side liquidity swept"

                        }


                    else:

                        invalid_sweep = True



            # ==============================================
            # Bearish Setup
            # Need Buy-side Liquidity Sweep
            # ==============================================

            elif direction == "Bearish":


                if (

                    zone.side == "Buy-side"

                    and

                    zone.swept

                ):


                    if getattr(

                        zone,

                        "sweep_valid",

                        False

                    ):


                        return {

                            "valid": True,

                            "reason":

                                "Buy-side liquidity swept"

                        }


                    else:

                        invalid_sweep = True



        if invalid_sweep:


            return {

                "valid": False,

                "reason":

                    "Liquidity sweep too deep"

            }



        return {

            "valid": False,

            "reason":

                "No liquidity confirmation"

        }

    # ======================================================
    # Determine Market Direction
    # ======================================================

    def determine_direction(
        self,
        bullish_score,
        bearish_score,
    ):


        if bullish_score > bearish_score:

            return "Bullish"



        elif bearish_score > bullish_score:

            return "Bearish"



        return "Neutral"



    # ======================================================
    # Analyze
    # ======================================================

    def analyze(self):


        decision = TradeDecision()


        score = 0

        bullish_score = 0

        bearish_score = 0


        reasons = []



        # ==================================================
        # Daily Bias
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



                if "Continuation" in structure.state:


                    score += 10


                    reasons.append(

                        "Trend continuation confirmed"

                    )



        # ==================================================
        # 15M Setup BOS
        # ==================================================

        if self.context.setup:


            if self.context.setup.bos.confirmed:


                score += 15



                if self.context.setup.bos.direction == "Bullish":


                    bullish_score += 15


                    reasons.append(

                        "15M bullish BOS confirmed"

                    )



                elif self.context.setup.bos.direction == "Bearish":


                    bearish_score += 15


                    reasons.append(

                        "15M bearish BOS confirmed"

                    )



        # ==================================================
        # 5M Entry BOS
        # ==================================================

        if self.context.entry:


            if self.context.entry.bos.confirmed:


                score += 10



                if self.context.entry.bos.direction == "Bullish":


                    bullish_score += 10


                    reasons.append(

                        "5M bullish BOS confirmation"

                    )



                elif self.context.entry.bos.direction == "Bearish":


                    bearish_score += 10


                    reasons.append(

                        "5M bearish BOS confirmation"

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
        # Determine Direction
        # ==================================================

        direction = self.determine_direction(

            bullish_score,

            bearish_score

        )



        # ==================================================
        # FVG Validation
        # ==================================================

        fresh_fvg = self.get_fresh_fvg()



        if direction == "Bullish":


            valid_fvg, ignored_fvg = (

                self.validate_fvg_direction(

                    "Bullish",

                    fresh_fvg

                )

            )


            if valid_fvg:


                score += 5


                reasons.append(

                    "Bullish FVG confirmation"

                )


            elif ignored_fvg:


                reasons.append(

                    "Opposite FVG ignored"

                )



        elif direction == "Bearish":


            valid_fvg, ignored_fvg = (

                self.validate_fvg_direction(

                    "Bearish",

                    fresh_fvg

                )

            )


            if valid_fvg:


                score += 5


                reasons.append(

                    "Bearish FVG confirmation"

                )


            elif ignored_fvg:


                reasons.append(

                    "Opposite FVG ignored"

                )



        # ==================================================
        # Liquidity Validation
        # ==================================================

        liquidity_result = self.validate_liquidity(

            direction

        )



        if liquidity_result["valid"]:


            score += 10


            reasons.append(

                liquidity_result["reason"]

            )


        else:


            reasons.append(

                liquidity_result["reason"]

            )

        # ==================================================
        # Confidence Calculation
        # ==================================================

        score = min(

            score,

            100

        )



        decision.confidence = score



        # ==================================================
        # Signal Generation
        # ==================================================

        if score < 40:


            decision.signal = "WAIT"



        elif score < 60:


            decision.signal = "WATCH"



        elif score < 80:


            if direction == "Bullish":


                decision.signal = "BUY"



            elif direction == "Bearish":


                decision.signal = "SELL"



            else:


                decision.signal = "WATCH"



        else:


            if direction == "Bullish":


                decision.signal = "STRONG BUY"



            elif direction == "Bearish":


                decision.signal = "STRONG SELL"



            else:


                decision.signal = "WATCH"




        # ==================================================
        # Pullback Validation
        # ==================================================

        if decision.signal in [

            "BUY",

            "STRONG BUY"

        ]:


            if self.context.entry:


                if self.context.entry.order_blocks:


                    decision.signal = (

                        "WAIT FOR PULLBACK"

                    )


                    reasons.append(

                        "Price waiting for Order Block pullback"

                    )




        elif decision.signal in [

            "SELL",

            "STRONG SELL"

        ]:


            if self.context.entry:


                if self.context.entry.order_blocks:


                    decision.signal = (

                        "WAIT FOR PULLBACK"

                    )


                    reasons.append(

                        "Price waiting for Order Block pullback"

                    )



        # ==================================================
        # Remove Duplicate Reasons
        # ==================================================

        decision.reasons = list(

            dict.fromkeys(

                reasons

            )

        )



        return decision