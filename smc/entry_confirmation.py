# smc/entry_confirmation.py

"""
BMIE Entry Confirmation Engine V3

Responsibilities
----------------
- Confirm execution after SMC setup validation
- Validate Order Block reaction
- Validate FVG reaction
- Ignore filled FVG
- Validate rejection candle
- Validate BOS / CHoCH confirmation
- Calculate confirmation confidence
- Generate entry confirmation state

Author: BMIE Project
"""


from typing import Any, List





class EntryConfirmationEngine:


    def __init__(
        self,
        current_price: float,
        direction: str,
        order_blocks: List,
        fair_value_gaps: List,
        liquidity=None,
        entry_context: Any = None,
    ):


        self.current_price = current_price

        self.direction = direction

        self.order_blocks = order_blocks

        self.fair_value_gaps = fair_value_gaps

        self.liquidity = liquidity or []

        self.entry_context = entry_context





    # ======================================================
    # Order Block Reaction
    # ======================================================

    def check_order_block_reaction(self):


        if not self.order_blocks:


            return {

                "valid": False,

                "reason":

                    "No Order Block available"

            }





        for block in self.order_blocks:



            if (

                block.low

                <=

                self.current_price

                <=

                block.high

            ):


                return {

                    "valid": True,

                    "reason":

                        "Price entered Order Block"

                }





        return {

            "valid": False,

            "reason":

                "Waiting for Order Block mitigation"

        }





    # ======================================================
    # FVG Reaction
    # ======================================================

    def check_fvg_reaction(self):


        if not self.fair_value_gaps:


            return {

                "valid": False,

                "reason":

                    "No valid FVG available"

            }





        valid_fvg_found = False





        for fvg in self.fair_value_gaps:



            # Ignore filled FVG

            if getattr(

                fvg,

                "filled",

                False

            ):


                continue





            valid_fvg_found = True





            if (

                fvg.low

                <=

                self.current_price

                <=

                fvg.high

            ):


                return {

                    "valid": True,

                    "reason":

                        "Price entered FVG"

                }





        if not valid_fvg_found:


            return {

                "valid": False,

                "reason":

                    "FVG already filled"

            }





        return {

            "valid": False,

            "reason":

                "Waiting for FVG reaction"

        }





    # ======================================================
    # Liquidity Confirmation
    # ======================================================

    def check_liquidity(self):


        if not self.liquidity:


            return {

                "valid": False,

                "reason":

                    "No liquidity confirmation"

            }





        for zone in self.liquidity:



            if getattr(

                zone,

                "swept",

                False

            ):


                return {

                    "valid": True,

                    "reason":

                        "Liquidity sweep confirmed"

                }





        return {

            "valid": False,

            "reason":

                "Waiting for liquidity sweep"

        }





    # ======================================================
    # Rejection Candle
    # ======================================================

    def check_rejection_candle(self):


        if not self.entry_context:


            return {

                "valid": False,

                "reason":

                    "No candle data"

            }





        candle = None





        if hasattr(

            self.entry_context,

            "df"

        ):


            try:

                candle = self.entry_context.df.iloc[-1]

            except Exception:

                candle = None





        if candle is None:


            candle = getattr(

                self.entry_context,

                "last_candle",

                None

            )





        if candle is None:


            return {

                "valid": False,

                "reason":

                    "No candle data"

            }





        try:


            if hasattr(

                candle,

                "open"

            ):


                open_price = candle.open

                high_price = candle.high

                low_price = candle.low

                close_price = candle.close


            else:


                open_price = candle["open"]

                high_price = candle["high"]

                low_price = candle["low"]

                close_price = candle["close"]



        except Exception:


            return {

                "valid": False,

                "reason":

                    "Invalid candle data"

            }





        body = abs(

            close_price -

            open_price

        )



        if body == 0:

            body = 0.0001





        upper_wick = (

            high_price -

            max(

                open_price,

                close_price

            )

        )



        lower_wick = (

            min(

                open_price,

                close_price

            )

            -

            low_price

        )





        if self.direction == "Bullish":


            if lower_wick >= body:


                return {

                    "valid": True,

                    "reason":

                        "Bullish rejection candle detected"

                }





        if self.direction == "Bearish":


            if upper_wick >= body:


                return {

                    "valid": True,

                    "reason":

                        "Bearish rejection candle detected"

                }





        return {

            "valid": False,

            "reason":

                "No rejection candle"

        }


# ================= PART 1 END =================

# ================= PART 2 START =================


    # ======================================================
    # Structure Confirmation
    # ======================================================

    def check_structure(self):


        if not self.entry_context:


            return {

                "valid": False,

                "reason":

                    "No entry structure"

            }





        reasons = []

        valid = False





        choch = getattr(

            self.entry_context,

            "choch",

            None

        )



        bos = getattr(

            self.entry_context,

            "bos",

            None

        )





        if choch:


            direction = getattr(

                choch,

                "direction",

                None

            )


            if direction:


                valid = True


                reasons.append(

                    f"{direction} CHoCH confirmed"

                )





        if bos:


            direction = getattr(

                bos,

                "direction",

                None

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

                "Waiting for BOS/CHoCH confirmation"

        }





    # ======================================================
    # Final Confirmation Analysis
    # ======================================================

    def analyze(self):


        result = {


            "confirmed": False,

            "status":

                "WAIT FOR CONFIRMATION",

            "confidence": 0,

            "reasons": []

        }





        ob_result = self.check_order_block_reaction()



        fvg_result = self.check_fvg_reaction()



        liquidity_result = self.check_liquidity()



        candle_result = self.check_rejection_candle()



        structure_result = self.check_structure()





        checks = [

            ob_result,

            fvg_result,

            liquidity_result,

            candle_result,

            structure_result,

        ]





        valid_count = 0





        for check in checks:



            result["reasons"].append(

                check["reason"]

            )



            if check["valid"]:


                valid_count += 1





        # ==================================================
        # Confidence Calculation
        # ==================================================

        confidence_map = {


            0: 0,

            1: 20,

            2: 45,

            3: 70,

            4: 85,

            5: 95,

        }





        result["confidence"] = (

            confidence_map.get(

                valid_count,

                0

            )

        )





        # ==================================================
        # Entry Trigger Logic
        #
        # Mandatory:
        #
        # 1. Liquidity
        # 2. OB or FVG reaction
        # 3. Candle OR Structure confirmation
        #
        # ==================================================


        zone_reaction = (

            ob_result["valid"]

            or

            fvg_result["valid"]

        )



        confirmation = (

            candle_result["valid"]

            or

            structure_result["valid"]

        )





        if (

            liquidity_result["valid"]

            and

            zone_reaction

            and

            confirmation

        ):


            result["confirmed"] = True


            result["status"] = (

                "ENTRY CONFIRMED"

            )


            result["confidence"] = max(

                result["confidence"],

                90

            )





        result["reasons"] = list(

            dict.fromkeys(

                result["reasons"]

            )

        )



        return result



# ================= PART 2 END =================