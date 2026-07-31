# smc/entry_validator.py

"""
BMIE Entry Validation Engine V6.

Responsibilities
----------------
- Validate trade entry conditions
- Detect pullback requirement
- Detect retracement phase
- Detect entry zone
- Validate directional FVG
- Validate liquidity alignment
- Validate BOS / CHoCH confirmation
- Use MTF context for execution direction

Author: BMIE Project
"""


from typing import List, Any


class EntryValidator:


    def __init__(
        self,
        current_price: float,
        trade_decision: Any,
        order_blocks: List,
        fair_value_gaps: List,
        liquidity: List,
        entry_context=None,
        setup_context=None,
        trend_context=None,
    ):


        self.current_price = current_price

        self.trade_decision = trade_decision

        self.order_blocks = order_blocks

        self.fair_value_gaps = fair_value_gaps

        self.liquidity = liquidity


        # MTF Context

        self.entry_context = entry_context

        self.setup_context = setup_context

        self.trend_context = trend_context





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
    # Extract Direction
    # ======================================================

    def extract_direction(self, event):


        if not event:

            return None



        direction = getattr(

            event,

            "direction",

            None

        )



        if direction:

            return str(direction).capitalize()



        return None





    # ======================================================
    # Direction Detection
    # ======================================================

    def get_direction(self):

        """
        Priority:

        1. 5M CHoCH
        2. 5M BOS
        3. 15M BOS
        4. 1H Trend
        5. Trade Signal
        """



        if self.entry_context:


            direction = self.extract_direction(

                getattr(

                    self.entry_context,

                    "choch",

                    None

                )

            )


            if direction:

                return direction





        if self.entry_context:


            direction = self.extract_direction(

                getattr(

                    self.entry_context,

                    "bos",

                    None

                )

            )


            if direction:

                return direction





        if self.setup_context:


            direction = self.extract_direction(

                getattr(

                    self.setup_context,

                    "bos",

                    None

                )

            )


            if direction:

                return direction





        if self.trend_context:


            direction = self.extract_direction(

                getattr(

                    self.trend_context,

                    "trend",

                    None

                )

            )


            if direction:

                return direction





        if self.trade_decision:


            signal = str(

                self.trade_decision.signal

            ).upper()



            if "BUY" in signal:

                return "Bullish"



            if "SELL" in signal:

                return "Bearish"




        return None





    # ======================================================
    # Order Block Validation
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

            block.low <= self.current_price

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


# ================= PART 1 END =================

# ================= PART 2 START =================


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


                    return {

                        "valid": True,

                        "reason":

                            "Bullish FVG confirmation"

                    }





            elif direction == "Bearish":


                if fvg_direction == "bearish":


                    return {

                        "valid": True,

                        "reason":

                            "Bearish FVG confirmation"

                    }





        return {

            "valid": False,

            "reason":

                "No directional FVG confirmation"

        }





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





        # fallback:
        # keep valid liquidity sweep as confirmation

        if self.liquidity:


            return {

                "valid": True,

                "reason":

                    "Liquidity sweep detected"

            }





        return {

            "valid": False,

            "reason":

                "Directional liquidity not available"

        }





    # ======================================================
    # Structure Validation
    # ======================================================

    def validate_structure(self):


        reasons = []

        valid = False





        if self.entry_context:



            choch = getattr(

                self.entry_context,

                "choch",

                None

            )



            if choch:


                direction = self.extract_direction(

                    choch

                )


                if direction:


                    valid = True


                    reasons.append(

                        f"{direction} CHoCH detected"

                    )





            bos = getattr(

                self.entry_context,

                "bos",

                None

            )



            if bos:


                direction = self.extract_direction(

                    bos

                )


                if direction:


                    valid = True


                    reasons.append(

                        f"{direction} BOS confirmed"

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

                "No structure confirmation"

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





        ob_result = self.validate_order_block()



        result["reasons"].append(

            ob_result["reason"]

        )



        if not ob_result["valid"]:


            result["valid"] = False

            result["status"] = ob_result["state"]





        structure_result = self.validate_structure()



        result["reasons"].append(

            structure_result["reason"]

        )





        fvg_result = self.validate_fvg()



        result["reasons"].append(

            fvg_result["reason"]

        )





        liquidity_result = self.validate_liquidity()



        result["reasons"].append(

            liquidity_result["reason"]

        )





        if not liquidity_result["valid"]:


            result["valid"] = False





        if (

            structure_result["valid"]

            and

            fvg_result["valid"]

            and

            liquidity_result["valid"]

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





        result["reasons"] = list(

            dict.fromkeys(

                result["reasons"]

            )

        )



        return result



# ================= PART 2 END =================