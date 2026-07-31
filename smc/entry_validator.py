"""
smc/entry_validator.py

BMIE Entry Validation Engine V3.

Responsibilities
----------------
- Validate trade entry conditions
- Detect pullback requirement
- Detect retracement phase
- Detect entry zone
- Validate FVG direction
- Validate liquidity sweep
- Validate BOS / CHoCH confirmation
- Provide execution state

Author: BMIE Project
"""


from typing import List, Any, Optional





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
        structure: Optional[Any] = None,
    ):


        self.current_price = current_price

        self.trade_decision = trade_decision

        self.order_blocks = order_blocks

        self.fair_value_gaps = fair_value_gaps

        self.liquidity = liquidity

        self.structure = structure





    # ======================================================
    # Latest Order Block
    # ======================================================

    def latest_order_block(self):


        if not self.order_blocks:


            return None



        return sorted(

            self.order_blocks,

            key=lambda x: x.created_at,

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

                "reason":

                    "No Order Block available"

            }



        midpoint = (

            block.high +

            block.low

        ) / 2



        distance = abs(

            self.current_price -

            midpoint

        )



        percentage = (

            distance /

            self.current_price

        ) * 100





        if percentage > 2:


            return {

                "valid": False,

                "state":

                    "WAIT FOR PULLBACK",

                "reason":

                    "Price extended from Order Block"

            }





        elif percentage > 0.5:


            return {

                "valid": False,

                "state":

                    "WAIT FOR RETRACEMENT",

                "reason":

                    "Waiting for Order Block mitigation"

            }





        elif (

            block.low

            <= self.current_price

            <= block.high

        ):


            return {

                "valid": False,

                "state":

                    "ENTRY ZONE",

                "reason":

                    "Price inside Order Block"

            }





        return {

            "valid": True,

            "state":

                "ENTRY READY",

            "reason":

                "Order Block location valid"

        }





    # ======================================================
    # Trade Direction
    # ======================================================

    def get_direction(self):


        if not self.trade_decision:


            return None



        signal = str(

            self.trade_decision.signal

        ).upper()



        if "BUY" in signal:


            return "Bullish"



        if "SELL" in signal:


            return "Bearish"



        return None





    # ======================================================
    # FVG Validation
    # ======================================================

    def validate_fvg(self):


        direction = self.get_direction()



        if not self.fair_value_gaps:


            return {

                "valid": False,

                "reason":

                    "No FVG available"

            }



        valid_fvg = []



        for fvg in self.fair_value_gaps:



            if getattr(

                fvg,

                "filled",

                False

            ):


                continue



            fvg_direction = str(

                getattr(

                    fvg,

                    "direction",

                    ""

                )

            ).lower()



            if direction == "Bullish":


                if fvg_direction == "bullish":


                    valid_fvg.append(fvg)



            elif direction == "Bearish":


                if fvg_direction == "bearish":


                    valid_fvg.append(fvg)



        if valid_fvg:


            return {

                "valid": True,

                "reason":

                    "Directional FVG confirmation"

            }



        return {

            "valid": False,

            "reason":

                "No directional FVG confirmation"

        }


# ================= PART 1 END =================

# ================= PART 2 START =================


    # ======================================================
    # Liquidity Validation
    # ======================================================

    def validate_liquidity(self):


        direction = self.get_direction()



        if not self.liquidity:


            return {

                "valid": False,

                "reason":

                    "No liquidity confirmation"

            }




        for zone in self.liquidity:



            if not getattr(

                zone,

                "swept",

                False

            ):


                continue




            side = getattr(

                zone,

                "side",

                ""

            )



            if direction == "Bullish":


                if side == "Sell-side":


                    return {

                        "valid": True,

                        "reason":

                            "Sell-side liquidity swept"

                    }




            elif direction == "Bearish":


                if side == "Buy-side":


                    return {

                        "valid": True,

                        "reason":

                            "Buy-side liquidity swept"

                    }





        return {

            "valid": False,

            "reason":

                "Directional liquidity not available"

        }





    # ======================================================
    # Structure Confirmation
    # ======================================================

    def validate_structure(self):


        if not self.structure:


            return {

                "valid": False,

                "reason":

                    "No structure confirmation"

            }




        reasons = []



        valid = False



        if getattr(

            self.structure,

            "bos",

            None

        ):


            if self.structure.bos.confirmed:


                valid = True


                reasons.append(

                    "BOS confirmed"

                )





        if getattr(

            self.structure,

            "choch",

            None

        ):


            if self.structure.choch.confirmed:


                valid = True


                reasons.append(

                    "CHoCH confirmed"

                )





        if valid:


            return {

                "valid": True,

                "reason":

                    " + ".join(reasons)

            }





        return {

            "valid": False,

            "reason":

                "No BOS/CHoCH confirmation"

        }





    # ======================================================
    # Final Analysis
    # ======================================================

    def analyze(self):


        result = {


            "valid": True,


            "status":

                "READY",


            "reasons": []

        }




        if not self.trade_decision:


            return {


                "valid": False,


                "status":

                    "WAIT",


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



        if not liquidity_result["valid"]:


            result["valid"] = False





        # ----------------------------------------------
        # Structure
        # ----------------------------------------------

        structure_result = self.validate_structure()



        result["reasons"].append(

            structure_result["reason"]

        )





        # ----------------------------------------------
        # Final Entry Decision
        # ----------------------------------------------

        if (

            fvg_result["valid"]

            and

            liquidity_result["valid"]

            and

            structure_result["valid"]

            and

            ob_result["valid"]

        ):


            result["status"] = (

                "ENTRY CONFIRMED"

            )


            result["valid"] = True



        elif result["status"] == "READY":


            result["status"] = (

                "WAIT FOR CONFIRMATION"

            )





        # Remove duplicate reasons

        result["reasons"] = list(

            dict.fromkeys(

                result["reasons"]

            )

        )



        return result



# ================= PART 2 END =================