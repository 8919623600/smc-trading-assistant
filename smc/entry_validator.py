"""
smc/entry_validator.py

BMIE Entry Validation Engine.

Responsibilities
----------------
- Validate BUY / SELL decisions
- Check Order Block distance
- Check FVG confirmation
- Validate retracement requirement
- Provide final entry status

Author: BMIE Project
"""


from typing import List, Any



class EntryValidator:
    """
    Validates whether a trade setup
    is ready for execution.
    """



    def __init__(
        self,
        current_price: float,
        trade_decision: Any,
        order_blocks: List,
        fair_value_gaps: List,
        liquidity: List,
    ):

        self.current_price = current_price

        self.trade_decision = trade_decision

        self.order_blocks = order_blocks

        self.fair_value_gaps = fair_value_gaps

        self.liquidity = liquidity



    # ======================================================
    # Order Block Validation
    # ======================================================

    def validate_order_block(self):


        if not self.order_blocks:

            return False, "No Order Block available"



        latest_ob = sorted(

            self.order_blocks,

            key=lambda x:x.created_at,

            reverse=True

        )[0]



        midpoint = (

            latest_ob.high

            +
            latest_ob.low

        ) / 2



        distance = abs(

            self.current_price

            -
            midpoint

        )



        percentage = (

            distance

            /
            self.current_price

        ) * 100



        if percentage > 2:


            return (

                False,

                "Order Block too far from current price"

            )



        return (

            True,

            "Order Block location valid"

        )



    # ======================================================
    # FVG Validation
    # ======================================================

    def validate_fvg(self):


        if not self.fair_value_gaps:

            return (

                False,

                "No FVG available"

            )



        latest_fvg = sorted(

            self.fair_value_gaps,

            key=lambda x:x.created_at,

            reverse=True

        )[0]



        if latest_fvg.filled:


            return (

                False,

                "FVG already filled"

            )



        return (

            True,

            "Fresh FVG available"

        )



    # ======================================================
    # Liquidity Validation
    # ======================================================

    def validate_liquidity(self):


        if self.liquidity:


            return (

                True,

                "Liquidity confirmation available"

            )



        return (

            False,

            "No liquidity confirmation"

        )



    # ======================================================
    # Final Validation
    # ======================================================

    def analyze(self):


        result = {

            "valid": True,

            "status": "READY",

            "reasons": []

        }



        if not self.trade_decision:


            result["valid"] = False

            result["status"] = "WAIT"

            result["reasons"].append(

                "No trade decision"

            )


            return result



        if self.trade_decision.signal in [

            "WAIT",

            "WATCH"

        ]:


            result["valid"] = False

            result["status"] = "WAIT"



        # Order Block

        ob_valid, ob_reason = (

            self.validate_order_block()

        )


        result["reasons"].append(

            ob_reason

        )



        if not ob_valid:


            result["valid"] = False

            result["status"] = (

                "WAIT FOR RETRACEMENT"

            )



        # FVG

        fvg_valid, fvg_reason = (

            self.validate_fvg()

        )


        result["reasons"].append(

            fvg_reason

        )



        # Liquidity

        liq_valid, liq_reason = (

            self.validate_liquidity()

        )


        result["reasons"].append(

            liq_reason

        )



        return result