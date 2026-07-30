"""
smc/setup_quality.py

BMIE Setup Quality Engine.

Responsibilities
----------------
- Score trade setup quality
- Evaluate HTF alignment
- Evaluate liquidity
- Evaluate Order Block quality
- Evaluate FVG freshness
- Generate setup grade

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
    Stores setup quality evaluation.
    """

    score: int = 0

    grade: str = "D"

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
    Evaluates overall SMC setup quality.
    """



    def __init__(
        self,
        context,
        order_block=None,
        liquidity=None,
        fvg=None,
    ):

        self.context = context

        self.order_block = order_block

        self.liquidity = liquidity

        self.fvg = fvg




    # ======================================================
    # Grade Calculation
    # ======================================================

    def calculate_grade(
        self,
        score
    ):


        if score >= 85:

            return "A+"



        elif score >= 75:

            return "A"



        elif score >= 65:

            return "B"



        elif score >= 50:

            return "C"



        return "D"





    # ======================================================
    # Analyze
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


            if hasattr(
                self.context.bias,
                "market_structure"
            ):


                trend = (

                    self.context.bias.market_structure.trend

                )



                if trend == "Bullish":


                    score += 15

                    strengths.append(

                        "Daily bullish bias"

                    )



                elif trend == "Bearish":


                    score += 15

                    strengths.append(

                        "Daily bearish bias"

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
        # 1H Trend
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

                else:


                    warnings.append(

                        "No 1H continuation"

                    )





        # ==================================================
        # Order Block
        # ==================================================

        if self.order_block:


            if hasattr(
                self.order_block,
                "distance"
            ):


                if self.order_block.distance == "Valid":


                    score += 10


                    strengths.append(

                        "Valid Order Block"

                    )


                else:


                    score -= 10


                    warnings.append(

                        "Order Block far"

                    )


        else:


            warnings.append(

                "No Order Block"

            )





        # ==================================================
        # Liquidity
        # ==================================================

        if self.liquidity:


            if (

                self.liquidity.swept

                and

                self.liquidity.sweep_valid

            ):


                score += 15


                strengths.append(

                    "Valid liquidity sweep"

                )


            else:


                score -= 15


                warnings.append(

                    "Invalid liquidity"

                )


        else:


            warnings.append(

                "No liquidity confirmation"

            )





        # ==================================================
        # FVG
        # ==================================================

        if self.fvg:


            if self.fvg.filled:


                score -= 5


                warnings.append(

                    "FVG already filled"

                )


            else:


                score += 5


                strengths.append(

                    "Fresh FVG"

                )





        # ==================================================
        # Final Result
        # ==================================================

        score = max(

            0,

            min(

                score,

                100

            )

        )



        result.score = score

        result.grade = self.calculate_grade(

            score

        )


        result.strengths = strengths

        result.warnings = warnings



        return result