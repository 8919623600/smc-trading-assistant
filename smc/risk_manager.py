"""
smc/risk_manager.py

BMIE Risk Manager V5

Changes
-------
- Adds realistic RR control
- Adds entry zone support
- Adds safer target validation
- Keeps compatibility with MarketEngine
- Keeps RiskDecision API compatible

Author: BMIE Project
"""

from dataclasses import dataclass


@dataclass
class RiskDecision:

    valid: bool = False

    direction: str = None

    entry: float = None

    entry_low: float = None

    entry_high: float = None

    stop_loss: float = None

    target: float = None

    risk_amount: float = 0

    reward_amount: float = 0

    risk_reward: float = 0

    position_size: float = 0

    reason: str = ""



class RiskManager:


    def __init__(
        self,
        account_balance: float,
        risk_percent: float = 1,
        minimum_rr: float = 2,
        maximum_rr: float = 8
    ):

        self.account_balance = account_balance

        self.risk_percent = risk_percent

        self.minimum_rr = minimum_rr

        self.maximum_rr = maximum_rr



    def calculate_risk_amount(self):

        return (
            self.account_balance
            *
            self.risk_percent
            /
            100
        )



    def get_direction(self, trade_decision):

        signal = str(
            getattr(
                trade_decision,
                "signal",
                ""
            )
        ).upper()


        if "BUY" in signal:

            return "Bullish"


        if "SELL" in signal:

            return "Bearish"


        return None



    def calculate_entry(
        self,
        trade_decision,
        order_blocks
    ):

        if order_blocks:

            block = order_blocks[0]

            return (
                block.high +
                block.low
            ) / 2


        return getattr(
            trade_decision,
            "price",
            None
        )



    def calculate_entry_zone(
        self,
        order_blocks
    ):

        if not order_blocks:

            return None, None


        block = order_blocks[0]


        return (
            block.low,
            block.high
        )



    def calculate_stop_loss(
        self,
        direction,
        order_blocks
    ):

        if not order_blocks:

            return None


        block = order_blocks[0]


        buffer = abs(
            block.high -
            block.low
        ) * 0.2


        if direction == "Bullish":

            return block.low - buffer


        if direction == "Bearish":

            return block.high + buffer


        return None



    def calculate_target(
        self,
        direction,
        liquidity
    ):

        if not liquidity:

            return None


        return getattr(
            liquidity,
            "level",
            None
        )



    def calculate_position_size(
        self,
        risk_amount,
        entry,
        stop_loss
    ):

        if not entry or not stop_loss:

            return 0


        distance = abs(
            entry -
            stop_loss
        )


        if distance == 0:

            return 0


        return risk_amount / distance



    def calculate_reward(
        self,
        entry,
        target
    ):

        if not entry or not target:

            return 0


        return abs(
            target -
            entry
        )



    def adjust_target(
        self,
        entry,
        stop_loss,
        target,
        direction
    ):

        if not entry or not stop_loss or not target:

            return target


        risk = abs(
            entry -
            stop_loss
        )


        reward = abs(
            target -
            entry
        )


        rr = reward / risk if risk else 0


        if rr <= self.maximum_rr:

            return target


        if direction == "Bullish":

            return entry + (
                risk *
                self.maximum_rr
            )


        if direction == "Bearish":

            return entry - (
                risk *
                self.maximum_rr
            )


        return target



    def analyze(
        self,
        trade_decision,
        order_blocks,
        liquidity=None
    ):


        result = RiskDecision()


        direction = self.get_direction(
            trade_decision
        )


        if not direction:

            result.reason = "Direction unavailable"

            return result



        entry = self.calculate_entry(
            trade_decision,
            order_blocks
        )


        stop_loss = self.calculate_stop_loss(
            direction,
            order_blocks
        )


        target = self.calculate_target(
            direction,
            liquidity
        )


        target = self.adjust_target(
            entry,
            stop_loss,
            target,
            direction
        )


        entry_low, entry_high = self.calculate_entry_zone(
            order_blocks
        )


        risk_amount = self.calculate_risk_amount()


        reward = self.calculate_reward(
            entry,
            target
        )


        risk_distance = abs(
            entry -
            stop_loss
        ) if entry and stop_loss else 0


        rr = 0


        if risk_distance:

            rr = reward / risk_distance



        position_size = self.calculate_position_size(
            risk_amount,
            entry,
            stop_loss
        )


        result.direction = direction

        result.entry = entry

        result.entry_low = entry_low

        result.entry_high = entry_high

        result.stop_loss = stop_loss

        result.target = target

        result.risk_amount = risk_amount

        result.reward_amount = reward

        result.risk_reward = round(
            rr,
            2
        )

        result.position_size = round(
            position_size,
            2
        )


        if (
            rr >= self.minimum_rr
            and rr <= self.maximum_rr
        ):

            result.valid = True

            result.reason = "Valid risk reward setup"


        elif rr > self.maximum_rr:

            result.valid = False

            result.reason = "RR above maximum limit"


        else:

            result.valid = False

            result.reason = "Risk reward below minimum"



        return result
