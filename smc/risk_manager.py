"""
smc/risk_manager.py

BMIE Risk Manager V4

Adds:
- Risk input debugging
- Backtest fallback direction
- Safe risk generation
"""

from dataclasses import dataclass


@dataclass
class RiskDecision:

    valid: bool = False
    direction: str = None
    entry: float = None
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
    ):

        self.account_balance = account_balance
        self.risk_percent = risk_percent
        self.minimum_rr = minimum_rr


    def calculate_risk_amount(self):

        return (
            self.account_balance *
            self.risk_percent /
            100
        )


    def get_direction(
        self,
        trade_decision,
        order_blocks=None
    ):

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


        if order_blocks:

            block = order_blocks[0]

            block_type = getattr(
                block,
                "direction",
                getattr(block, "type", "")
            )


            if block_type == "Bullish":
                return "Bullish"


            if block_type == "Bearish":
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


    def calculate_stop_loss(
        self,
        direction,
        order_blocks
    ):

        if not order_blocks:
            return None


        block = order_blocks[0]

        buffer = (
            abs(
                block.high -
                block.low
            ) * 0.2
        )


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
            entry - stop_loss
        )


        if distance == 0:
            return 0


        return risk_amount / distance


    def analyze(
        self,
        trade_decision,
        order_blocks,
        liquidity=None
    ):

        result = RiskDecision()


        direction = self.get_direction(
            trade_decision,
            order_blocks
        )


        print("RISK INPUT DEBUG")
        print("Direction:", direction)
        print(
            "Order Blocks:",
            len(order_blocks) if order_blocks else 0
        )
        print(
            "Liquidity:",
            liquidity
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


        risk_amount = self.calculate_risk_amount()


        reward = 0

        if entry and target:
            reward = abs(
                target - entry
            )


        risk_distance = 0

        if entry and stop_loss:
            risk_distance = abs(
                entry - stop_loss
            )


        rr = 0

        if risk_distance:
            rr = reward / risk_distance


        result.direction = direction
        result.entry = entry
        result.stop_loss = stop_loss
        result.target = target
        result.risk_amount = risk_amount
        result.reward_amount = reward
        result.risk_reward = round(rr, 2)
        result.position_size = round(
            self.calculate_position_size(
                risk_amount,
                entry,
                stop_loss
            ),
            2
        )


        if rr >= self.minimum_rr:

            result.valid = True
            result.reason = "Valid risk reward setup"

        else:

            result.valid = False
            result.reason = "Risk reward below minimum"


        return result
