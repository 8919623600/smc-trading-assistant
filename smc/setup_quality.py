"""
smc/setup_quality.py

BMIE Setup Quality Engine V2.

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





@dataclass
class SetupQualityResult:


    score: int = 0

    grade: str = "D"

    state: str = "WAIT FOR PULLBACK"


    strengths: List[str] = field(

        default_factory=list

    )


    warnings: List[str] = field(

        default_factory=list

    )





class SetupQualityEngine:


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
    # Detect Market Direction
    # ======================================================

    def get_direction(self):


        if self.context.trend:


            structure = getattr(

                self.context.trend,

                "market_structure",

                None

            )


            if structure:


                trend = getattr(

                    structure,

                    "trend",

                    None

                )


                if trend:

                    return trend





        return None





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



        direction = self.get_direction()





        # ==================================================
        # Daily Bias
        # ==================================================

        if self.context.bias:


            structure = getattr(

                self.context.bias,

                "market_structure",

                None

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


            structure = getattr(

                self.context.structure,

                "market_structure",

                None

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
        # 1H Trend
        # ==================================================

        if self.context.trend:


            structure = getattr(

                self.context.trend,

                "market_structure",

                None

            )


            if structure:


                if "Continuation" in structure.state:


                    score += 20


                    strengths.append(

                        "1H trend continuation"

                    )


# ================= PART 1 END =================

# ================= PART 2 START =================


                else:


                    score += 10


                    strengths.append(

                        "1H trend confirmed"

                    )





        # ==================================================
        # Order Block
        # ==================================================

        if self.order_block:


            score += 15


            strengths.append(

                "Fresh Order Block"

            )


        else:


            warnings.append(

                "No Order Block"

            )





        # ==================================================
        # Liquidity
        # ==================================================

        if self.liquidity:


            swept = getattr(

                self.liquidity,

                "swept",

                False

            )



            valid = getattr(

                self.liquidity,

                "sweep_valid",

                False

            )



            if swept and valid:


                score += 15


                strengths.append(

                    "Valid liquidity sweep"

                )



            else:


                warnings.append(

                    "Liquidity sweep not confirmed"

                )





        else:


            warnings.append(

                "No liquidity confirmation"

            )





        # ==================================================
        # FVG Logic V2
        #
        # Important:
        #
        # Same direction filled FVG:
        #     Negative
        #
        # Opposite direction filled FVG:
        #     Neutral
        #
        # Fresh FVG:
        #     Positive
        #
        # ==================================================

        if self.fvg:



            fvg_direction = str(

                getattr(

                    self.fvg,

                    "direction",

                    ""

                )

            ).lower()



            filled = getattr(

                self.fvg,

                "filled",

                False

            )





            market_direction = str(

                direction

                or ""

            ).lower()





            if filled:



                if (

                    fvg_direction

                    and

                    market_direction

                    and

                    fvg_direction

                    in

                    market_direction

                ):


                    score -= 5


                    warnings.append(

                        "Directional FVG filled"

                    )


                else:


                    strengths.append(

                        "Opposite FVG ignored"

                    )





            else:


                score += 10


                strengths.append(

                    "Fresh FVG"

                )





        else:


            warnings.append(

                "No FVG"

            )





        # ==================================================
        # Normalize Score
        # ==================================================

        if score < 0:

            score = 0



        if score > 100:

            score = 100





        result.score = score


        result.grade = self.calculate_grade(

            score

        )



        result.strengths = list(

            dict.fromkeys(

                strengths

            )

        )



        result.warnings = list(

            dict.fromkeys(

                warnings

            )

        )





        # ==================================================
        # Setup State
        # ==================================================

        if score >= 80:


            result.state = (

                "HIGH QUALITY SETUP"

            )


        elif score >= 65:


            result.state = (

                "GOOD QUALITY SETUP"

            )


        elif score >= 50:


            result.state = (

                "MODERATE SETUP"

            )


        else:


            result.state = (

                "WEAK SETUP"

            )





        return result



# ================= PART 2 END =================