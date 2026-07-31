# smc/entry_confirmation.py

"""
BMIE Entry Confirmation Engine V2

Responsibilities
----------------
- Confirm execution after SMC setup validation
- Validate Order Block reaction
- Validate FVG reaction
- Validate rejection candle
- Validate BOS / CHoCH confirmation
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
        entry_context: Any = None,
    ):


        self.current_price = current_price

        self.direction = direction

        self.order_blocks = order_blocks

        self.fair_value_gaps = fair_value_gaps

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

                        "Price reacting from Order Block"

                }





        return {

            "valid": False,

            "reason":

                "Price not inside Order Block"

        }





    # ======================================================
    # FVG Reaction
    # ======================================================

    def check_fvg_reaction(self):


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

                        "Price reacting from FVG"

                }





        return {

            "valid": False,

            "reason":

                "Price not inside FVG"

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



        # ----------------------------------------------
        # New support: DataFrame candle
        # ----------------------------------------------

        if hasattr(

            self.entry_context,

            "df"

        ):


            try:


                candle = self.entry_context.df.iloc[-1]


            except Exception:


                candle = None





        # ----------------------------------------------
        # Backward compatibility
        # ----------------------------------------------

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





        # Avoid zero body issue

        if body == 0:


            body = 0.0001





        if self.direction == "Bullish":


            if lower_wick > body:


                return {

                    "valid": True,

                    "reason":

                        "Bullish rejection candle detected"

                }





        elif self.direction == "Bearish":


            if upper_wick > body:


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





        return {

            "valid": valid,

            "reason":

                " + ".join(reasons)

                if reasons

                else

                "No BOS/CHoCH confirmation"

        }





    # ======================================================
    # Final Confirmation
    # ======================================================

    def analyze(self):


        result = {


            "confirmed": False,

            "status":

                "WAIT FOR CONFIRMATION",

            "reasons": []

        }





        checks = [


            self.check_order_block_reaction(),


            self.check_fvg_reaction(),


            self.check_rejection_candle(),


            self.check_structure(),


        ]





        valid_count = 0





        for check in checks:



            result["reasons"].append(

                check["reason"]

            )



            if check["valid"]:


                valid_count += 1





        # --------------------------------------------------
        # Entry trigger rule
        #
        # Minimum:
        # - OB/FVG reaction
        # - Rejection candle
        # - BOS/CHoCH
        #
        # Any 3 confirmations
        # --------------------------------------------------

        if valid_count >= 3:


            result["confirmed"] = True


            result["status"] = (

                "ENTRY CONFIRMED"

            )





        result["reasons"] = list(

            dict.fromkeys(

                result["reasons"]

            )

        )



        return result