"""
smc/setup_quality.py

BMIE Setup Quality Engine V3

Responsibilities
----------------
- Evaluate SMC setup strength
- Score confluence
- Handle FVG mitigation correctly
- Generate setup grade

Author: BMIE Project
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class SetupQualityResult:

    score: int = 0
    grade: str = "D"
    state: str = "WAIT"

    strengths: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class SetupQualityEngine:


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


    def get_direction(self):

        if self.context.trend:

            state = getattr(
                self.context.trend,
                "market_state",
                None
            )

            if state:

                trend = getattr(
                    state,
                    "trend",
                    None
                )

                if trend:
                    return str(trend).lower()

        return ""


    def calculate_grade(self, score):

        if score >= 80:
            return "A"

        if score >= 65:
            return "B"

        if score >= 50:
            return "C"

        return "D"


    def analyze(self):

        result = SetupQualityResult()

        score = 0
        strengths = []
        warnings = []

        direction = self.get_direction()


        # Daily Bias

        if self.context.bias:

            score += 10

            strengths.append(
                "Daily bias analyzed"
            )


        # 4H Structure

        if self.context.structure:

            score += 10

            strengths.append(
                "4H structure analyzed"
            )


        # 1H Trend

        if self.context.trend:

            score += 20

            strengths.append(
                "1H trend continuation"
            )


        # Order Block

        if self.order_block:

            score += 15

            strengths.append(
                "Fresh Order Block"
            )

        else:

            warnings.append(
                "No Order Block"
            )


        # Liquidity

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
                    "Liquidity not confirmed"
                )


        # FVG V3 Logic

        if self.fvg:

            filled = getattr(
                self.fvg,
                "filled",
                False
            )

            fvg_direction = str(
                getattr(
                    self.fvg,
                    "direction",
                    ""
                )
            ).lower()


            if not filled:

                score += 10

                strengths.append(
                    "Fresh FVG"
                )

            else:

                if (
                    direction
                    and
                    direction in fvg_direction
                ):

                    score -= 2

                    warnings.append(
                        "Directional FVG mitigated"
                    )

                else:

                    strengths.append(
                        "Opposite FVG ignored"
                    )


        # Normalize

        score = max(
            0,
            min(
                score,
                100
            )
        )


        result.score = score
        result.grade = self.calculate_grade(score)

        result.strengths = list(
            dict.fromkeys(strengths)
        )

        result.warnings = list(
            dict.fromkeys(warnings)
        )


        if score >= 80:

            result.state = "HIGH QUALITY SETUP"

        elif score >= 65:

            result.state = "GOOD QUALITY SETUP"

        elif score >= 50:

            result.state = "MODERATE SETUP"

        else:

            result.state = "WEAK SETUP"


        return result
