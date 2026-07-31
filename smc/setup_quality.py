"""
smc/setup_quality.py

BMIE Setup Quality Engine.

Responsibilities
----------------
- Evaluate setup strength
- Score SMC confluence
- Identify setup weaknesses
- Generate setup grade
- Provide setup state

Author: BMIE Project
"""


from dataclasses import dataclass, field
from typing import List





# ==========================================================
# Setup Quality Result
# ==========================================================

@dataclass
class SetupQualityResult:
    """
    Represents setup quality evaluation.
    """

    score: int = 0

    grade: str = "D"

    state: str = "WAIT FOR PULLBACK"


    strengths: List[str] = field(

        default_factory=list

    )


    warnings: List[str] = field(

        default_factory=list

    )





# ==========================================================
# Setup Quality Engine
# ==========================================================

class SetupQualityEngine:
    """
    Evaluates BMIE trade setup quality.
    """



    def __init__(
        self,
        context,
        liquidity=None,
        fvg=None,
        order_block=None,
    ):


        self.context = context

        self.liquidity = liquidity

        self.fvg = fvg

        self.order_block = order_block





    # ======================================================
    # Grade Calculation
    # ======================================================

    def calculate_grade(
        self,
        score: int,
    ):


        if score >= 80:


            return "A"



        elif score >= 65:


            return "B"



        elif score >= 50:


            return "C"



        else:


            return "D"





    # ======================================================
    # Main Evaluation
    # ======================================================

    def analyze(self):


        result = SetupQualityResult()



        score = 0



        strengths = []

        warnings = []





        # ==================================================
        # Daily Bias
        # ==================================================

        if self.context.bias:


            structure = (

                self.context.bias.market_structure

            )


            if structure:


                if structure.trend in [

                    "Bullish",

                    "Bearish"

                ]:


                    score += 15


                    strengths.append(

                        "Daily bias aligned"

                    )


                else:


                    score -= 5


                    warnings.append(

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


                if structure.trend in [

                    "Bullish",

                    "Bearish"

                ]:


                    score += 15


                    strengths.append(

                        "4H structure aligned"

                    )


                else:


                    score -= 5


                    warnings.append(

                        "4H structure transition"

                    )





        # ==================================================
        # 1H Trend Continuation
        # ==================================================

        if self.context.trend:


            structure = (

                self.context.trend.market_structure

            )


            if structure:


                if "Continuation" in structure.state:


                    score += 20


                    strengths.append(

                        "1H trend continuation"

                    )



# ================= PART 1 END =================

# ================= PART 2 START =================


        # ==================================================
        # 15M BOS Confirmation
        # ==================================================

        if self.context.setup:


            if self.context.setup.bos:


                if self.context.setup.bos.confirmed:


                    score += 10


                    strengths.append(

                        "15M BOS confirmation"

                    )





        # ==================================================
        # 5M BOS / CHoCH Confirmation
        # ==================================================

        if self.context.entry:



            if self.context.entry.bos:


                if self.context.entry.bos.confirmed:


                    score += 10


                    strengths.append(

                        "5M BOS confirmation"

                    )



            if self.context.entry.choch:


                if self.context.entry.choch.confirmed:


                    score += 10


                    strengths.append(

                        "5M CHoCH confirmation"

                    )





        # ==================================================
        # Order Block
        # ==================================================

        if self.order_block:



            if getattr(

                self.order_block,

                "status",

                None

            ) == "Fresh":


                score += 10


                strengths.append(

                    "Fresh Order Block"

                )


            else:


                score += 5


                warnings.append(

                    "Order Block not fresh"

                )



            if getattr(

                self.order_block,

                "distance",

                None

            ) == "Far":


                score -= 5


                warnings.append(

                    "Order Block far"

                )





        # ==================================================
        # Liquidity
        # ==================================================

        if self.liquidity:



            if getattr(

                self.liquidity,

                "swept",

                False

            ):


                if getattr(

                    self.liquidity,

                    "sweep_valid",

                    False

                ):


                    score += 15


                    strengths.append(

                        "Valid liquidity sweep"

                    )


                else:


                    score -= 5


                    warnings.append(

                        "Weak liquidity sweep"

                    )





        # ==================================================
        # FVG
        # ==================================================

        if self.fvg:



            if getattr(

                self.fvg,

                "filled",

                False

            ):


                score -= 5


                warnings.append(

                    "FVG filled"

                )


            else:


                score += 10


                strengths.append(

                    "Fresh FVG"

                )





        # ==================================================
        # Normalize Score
        # ==================================================

        score = max(

            0,

            min(

                score,

                100

            )

        )



        result.score = score



        result.grade = (

            self.calculate_grade(

                score

            )

        )



        result.state = (

            "WAIT FOR PULLBACK"

        )



        result.strengths = strengths



        result.warnings = warnings



        return result



# ================= PART 2 END =================