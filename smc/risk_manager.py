"""
risk/risk_manager.py

BMIE Risk Management Engine.

Responsibilities
----------------
- Calculate entry zone
- Calculate stop loss
- Calculate target
- Calculate risk reward
- Calculate position size
- Apply account risk rules

Author: BMIE Project
"""


from typing import Optional, Any


from models import RiskDecision



class RiskManager:
    """
    Calculates trade risk parameters
    from SMC trade setup.
    """



    def __init__(
        self,
        account_balance: float,
        risk_percent: float = 1.0,
        minimum_rr: float = 2.0,
    ):

        self.account_balance = account_balance

        self.risk_percent = risk_percent

        self.minimum_rr = minimum_rr



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
    # Position Size
    # ======================================================

    def calculate_position_size(
        self,
        risk_amount,
        risk_points,
    ):

        if risk_points <= 0:

            return 0.0


        return (
            risk_amount
            /
            risk_points
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



        # ==================================================
        # No Trade
        # ==================================================

        if not trade_decision:

            return result



        if trade_decision.signal == "WAIT":

            return result



        if not order_blocks:

            return result



        # ==================================================
        # Latest Order Block
        # ==================================================

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



        else:

            return result



        # ==================================================
        # Target 1:3 RR
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



        # ==================================================
        # Position Size
        # ==================================================

        risk_points = abs(

            result.entry_low

            -
            result.stop_loss

        )


        result.position_size = (

            self.calculate_position_size(

                result.risk_amount,

                risk_points

            )

        )



        return result