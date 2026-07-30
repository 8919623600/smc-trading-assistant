"""
smc/entry_validator.py

BMIE Entry Validation Engine V2.

Responsibilities
----------------
- Validate trade entry conditions
- Detect pullback requirement
- Detect retracement phase
- Detect entry zone
- Validate FVG
- Provide execution state

Author: BMIE Project
"""


from typing import List, Any



class EntryValidator:
    """
    Controls trade execution timing.
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
    # Latest Order Block
    # ======================================================

    def latest_order_block(self):

        if not self.order_blocks:

            return None


        return sorted(

            self.order_blocks,

            key=lambda x:x.created_at,

            reverse=True

        )[0]



    # ======================================================
    # Order Block Distance
    # ======================================================

    def validate_order_block(self):


        block = self.latest_order_block()



        if not block:


            return {

                "valid": False,

                "state": "WAIT",

                "reason": "No Order Block available"

            }



        midpoint = (

            block.high

            +
            block.low

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



        # ==============================================
        # Price far away
        # ==============================================

        if percentage > 2:


            return {

                "valid": False,

                "state": "WAIT FOR PULLBACK",

                "reason":

                    "Price extended from Order Block"

            }



        # ==============================================
        # Price approaching zone
        # ==============================================

        elif percentage > 0.5:


            return {

                "valid": False,

                "state": "WAIT FOR RETRACEMENT",

                "reason":

                    "Waiting for Order Block mitigation"

            }



        # ==============================================
        # Price inside zone
        # ==============================================

        elif (

            block.low

            <= self.current_price

            <= block.high

        ):


            return {

                "valid": False,

                "state": "ENTRY ZONE",

                "reason":

                    "Price inside Order Block"

            }



        return {

            "valid": True,

            "state": "ENTRY READY",

            "reason":

                "Order Block location valid"

        }



    # ======================================================
    # FVG Validation
    # ======================================================

    def validate_fvg(self):


        if not self.fair_value_gaps:


            return {

                "valid": False,

                "reason":

                    "No FVG available"

            }



        fresh = [

            fvg

            for fvg in self.fair_value_gaps

            if not fvg.filled

        ]



        if fresh:


            return {

                "valid": True,

                "reason":

                    "Fresh FVG confirmation"

            }



        return {

            "valid": False,

            "reason":

                "FVG already filled"

        }



    # ======================================================
    # Liquidity
    # ======================================================

    def validate_liquidity(self):


        if self.liquidity:


            return {

                "valid": True,

                "reason":

                    "Liquidity confirmation available"

            }



        return {

            "valid": False,

            "reason":

                "No liquidity confirmation"

            }



    # ======================================================
    # Final Analysis
    # ======================================================

    def analyze(self):


        result = {

            "valid": True,

            "status": "READY",

            "reasons": []

        }



        if not self.trade_decision:


            return {

                "valid": False,

                "status": "WAIT",

                "reasons":

                    [

                        "No trade decision"

                    ]

            }



        # ----------------------------------------------
        # Order Block
        # ----------------------------------------------

        ob_result = self.validate_order_block()



        result["reasons"].append(

            ob_result["reason"]

        )



        if not ob_result["valid"]:


            result["valid"] = False

            result["status"] = ob_result["state"]



        # ----------------------------------------------
        # FVG
        # ----------------------------------------------

        fvg_result = self.validate_fvg()



        result["reasons"].append(

            fvg_result["reason"]

        )



        # ----------------------------------------------
        # Liquidity
        # ----------------------------------------------

        liquidity_result = self.validate_liquidity()



        result["reasons"].append(

            liquidity_result["reason"]

        )



        # ----------------------------------------------
        # Existing weak signals
        # ----------------------------------------------

        if self.trade_decision.signal in [

            "WAIT",

            "WATCH"

        ]:


            result["valid"] = False

            result["status"] = "WAIT"



        return result