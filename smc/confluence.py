"""
smc/confluence.py

BMIE Confluence Engine V2

Responsibilities
----------------
- Combine multi timeframe structure
- Evaluate BOS / CHoCH
- Use setup quality and entry confirmation context
- Generate final trade decision

Author: BMIE Project
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class TradeDecision:

    signal: str = "WAIT FOR RETRACEMENT"

    confidence: float = 0

    reasons: List[str] = field(default_factory=list)


class ConfluenceEngine:


    def __init__(self, context):

        self.context = context



    def analyze(self):

        decision = TradeDecision()

        score = 0


        reasons = []


        bias = self.context.bias

        structure = self.context.structure

        trend = self.context.trend

        setup = self.context.setup

        entry = self.context.entry



        # -------------------------------
        # Higher timeframe
        # -------------------------------

        if bias:

            reasons.append(
                "Daily bias analyzed"
            )

            score += 10



        if structure:

            reasons.append(
                "4H structure analyzed"
            )

            score += 10



        # -------------------------------
        # Trend
        # -------------------------------

        if trend:

            state = getattr(
                trend,
                "market_state",
                None
            )

            if state:

                trend_state = str(
                    getattr(
                        state,
                        "phase",
                        ""
                    )
                ).lower()


                if "bullish" in trend_state:

                    score += 20

                    reasons.append(
                        "1H trend bullish"
                    )


                elif "bearish" in trend_state:

                    score += 20

                    reasons.append(
                        "1H trend bearish"
                    )



        # -------------------------------
        # Setup BOS / CHoCH
        # -------------------------------

        if setup:

            if getattr(setup, "bos", None):

                score += 10

                reasons.append(
                    "Setup BOS confirmed"
                )


            if getattr(setup, "choch", None):

                score += 5

                reasons.append(
                    "Setup CHoCH detected"
                )



        # -------------------------------
        # Entry confirmation priority
        # -------------------------------

        entry_confirmation = getattr(
            entry,
            "entry_confirmation",
            None
        )


        if entry_confirmation:


            status = str(
                entry_confirmation.get(
                    "status",
                    ""
                )
            ).upper()



            confidence = float(
                entry_confirmation.get(
                    "confidence",
                    0
                )
            )



            if "ENTRY CONFIRMED" in status:

                score += 25

                reasons.append(
                    "Entry confirmation passed"
                )


            elif "WAIT" in status:

                reasons.append(
                    "Waiting for entry confirmation"
                )



        # -------------------------------
        # Final decision
        # -------------------------------

        if score >= 80:


            decision.signal = "ENTRY READY"

            decision.confidence = min(
                score,
                95
            )


        elif score >= 60:


            decision.signal = "WAIT FOR RETRACEMENT"

            decision.confidence = score



        else:


            decision.signal = "NO TRADE"

            decision.confidence = score



        decision.reasons = reasons


        return decision
