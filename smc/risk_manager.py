"""
risk_manager.py

BMIE Risk Management Engine.

Responsibilities
----------------
- Calculate entry zone
- Calculate stop loss
- Calculate target
- Calculate risk reward
- Position sizing based on account risk

Author: BMIE Project
"""


from dataclasses import dataclass
from typing import Optional, Any



# ==========================================================
# Risk Model
# ==========================================================

@dataclass
class RiskDecision:
    """
    Stores trade risk parameters.
    """

    entry_low: Optional[float] = None

    entry_high: Optional[float] = None

    stop_loss: Optional[float] = None

    target: Optional[float] = None

    risk_reward: float = 0.0

    risk_amount: float = 0.0

    position_size: float = 0.0



# ==========================================================
# Risk Manager
# ==========================================================

class RiskManager:
    """
    Calculates trade risk parameters from SMC zones.
    """

    def __init__(
        self,
        account_balance: float,
        risk_percent: float = 1.0,
    ):

        self.account_balance = account_balance

        self.risk_percent = risk_percent



    # ======================================================
    # Risk Amount
    # ======================================================

    def calculate_risk_amount(self):

        return (
            self.account_balance
            *
            self.risk_percent
            /
            100
        )



    # ======================================================
    # Generate Risk Plan
    # ======================================================

    def analyze(
        self,
        trade_decision: Any,
        order_blocks: list,
    ) -> RiskDecision:


        result = RiskDecision()


        if not order_blocks:

            return result



        latest_ob = sorted(
            order_blocks,
            key=lambda x: x.created_at,
            reverse=True
        )[0]



        # ==================================================
        # Entry Zone
        # ==================================================

        result.entry_low = latest_ob.low

        result.entry_high = latest_ob.high



        # ==================================================
        # Stop Loss
        # ==================================================

        if latest_ob.direction == "Bullish":

            result.stop_loss = (
                latest_ob.low - 5
            )


        elif latest_ob.direction == "Bearish":

            result.stop_loss = (
                latest_ob.high + 5
            )



        # ==================================================
        # Target
        # ==================================================

        if latest_ob.direction == "Bullish":

            risk = (
                result.entry_low
                -
                result.stop_loss
            )

            result.target = (
                result.entry_high
                +
                (risk * 3)
            )



        elif latest_ob.direction == "Bearish":

            risk = (
                result.stop_loss
                -
                result.entry_high
            )

            result.target = (
                result.entry_low
                -
                (risk * 3)
            )



        # ==================================================
        # Risk Reward
        # ==================================================

        if result.stop_loss and result.target:


            risk = abs(
                result.entry_low
                -
                result.stop_loss
            )


            reward = abs(
                result.target
                -
                result.entry_low
            )


            if risk > 0:

                result.risk_reward = (
                    reward / risk
                )



        # ==================================================
        # Account Risk
        # ==================================================

        result.risk_amount = (
            self.calculate_risk_amount()
        )



        return result