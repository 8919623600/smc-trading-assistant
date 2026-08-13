"""
smc/risk_manager.py

BMIE Risk Manager V5.2

Changes:
- Preserve existing V5 logic
- Improved direction detection
- Supports:
    BUY / SELL
    Bullish / Bearish
    trade_decision.direction
    entry_confirmation.direction
- Better debugging compatibility
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
        maximum_rr: float = 8,
        current_price=None
    ):

        self.account_balance = account_balance
        self.risk_percent = risk_percent
        self.minimum_rr = minimum_rr
        self.maximum_rr = maximum_rr
        self.current_price = current_price



    def calculate_risk_amount(self):

        return (
            self.account_balance *
            self.risk_percent /
            100
        )



    # ======================================================
    # Direction Detection
    # ======================================================

    def get_direction(
        self,
        trade_decision
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



        # Explicit direction from MarketEngine

        direction = getattr(
            trade_decision,
            "direction",
            None
        )


        if direction:

            if direction.upper() in [
                "BUY",
                "BULLISH"
            ]:

                return "Bullish"


            if direction.upper() in [
                "SELL",
                "BEARISH"
            ]:

                return "Bearish"



        # Entry confirmation fallback

        confirmation = getattr(
            trade_decision,
            "entry_confirmation",
            None
        )


        if confirmation:


            direction = confirmation.get(
                "direction"
            )


            if direction:


                if direction.upper() in [
                    "BUY",
                    "BULLISH"
                ]:

                    return "Bullish"



                if direction.upper() in [
                    "SELL",
                    "BEARISH"
                ]:

                    return "Bearish"



        return None



    def calculate_entry(
        self,
        trade_decision,
        order_blocks
    ):


        current_price = self.current_price


        if current_price is None:

            current_price = getattr(
                self,
                "current_price",
                None
            )


        direction = self.get_direction(
            trade_decision
        )



        if order_blocks:


            block = order_blocks[0]


            high = getattr(
                block,
                "high",
                None
            )


            low = getattr(
                block,
                "low",
                None
            )


            if high is not None and low is not None:


                entry = (
                    high + low
                ) / 2



                # ======================================
                # Entry sanity validation
                # ======================================

                if current_price is not None:


                    distance = abs(
                        current_price - entry
                    )


                    # Reject extremely distant OB
                    # Allow maximum 3% deviation

                    max_distance = (
                        current_price * 0.03
                    )


                    if distance <= max_distance:

                        return entry


                    print(
                        "ENTRY REJECTED:",
                        "Current=",
                        current_price,
                        "OB Entry=",
                        entry
                    )



        # fallback

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

            getattr(
                block,
                "low",
                None
            ),

            getattr(
                block,
                "high",
                None
            )

        )



    def calculate_stop_loss(
        self,
        direction,
        order_blocks
    ):


        if not order_blocks:

            return None



        block = order_blocks[0]


        high = getattr(
            block,
            "high",
            None
        )


        low = getattr(
            block,
            "low",
            None
        )


        if high is None or low is None:

            return None



        buffer = abs(
            high - low
        ) * 0.2



        if direction == "Bullish":

            return low - buffer



        if direction == "Bearish":

            return high + buffer



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


        if entry is None or stop_loss is None:

            return 0



        distance = abs(
            entry - stop_loss
        )


        if distance == 0:

            return 0



        return (
            risk_amount /
            distance
        )



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

        print(
            "signal=", getattr(trade_decision, "signal", None),
            "direction=", direction,
            "order_blocks=", len(order_blocks) if order_blocks else 0,
            "liquidity=", liquidity
        )



        if not direction:

            result.reason = (
                "Direction unavailable"
            )

            return result



        entry = self.calculate_entry(
            trade_decision,
            order_blocks
        )

        print(
            "ENTRY DEBUG:",
            "entry=",
            entry,
            "current_price=",
            getattr(trade_decision, "current_price", None),
            "order_blocks=",
            len(order_blocks)
        )


        stop_loss = self.calculate_stop_loss(
            direction,
            order_blocks
        )


        target = self.calculate_target(
            direction,
            liquidity
        )



        entry_low, entry_high = (
            self.calculate_entry_zone(
                order_blocks
            )
        )



        result.direction = direction

        result.entry = entry

        result.entry_low = entry_low

        result.entry_high = entry_high

        result.stop_loss = stop_loss

        result.target = target



        if entry is None:

            result.reason = (
                "Entry unavailable"
            )

            return result



        if stop_loss is None:

            result.reason = (
                "Stop loss unavailable"
            )

            return result


        if target is None:

            result.reason = (
                "Target unavailable"
            )

            return result


        # ======================================================
        # Direction Validation
        # ======================================================

        if direction == "Bullish":

            if target <= entry:

                result.reason = (
                    "Invalid bullish target below entry"
                )

                return result


            if stop_loss >= entry:

                result.reason = (
                    "Invalid bullish stop loss above entry"
                )

                return result



        if direction == "Bearish":

            if target >= entry:

                result.reason = (
                    "Invalid bearish target above entry"
                )

                return result


            if stop_loss <= entry:

                result.reason = (
                    "Invalid bearish stop loss below entry"
                )

                return result



        risk_distance = abs(
            entry - stop_loss
        )


        reward_distance = abs(
            target - entry
        )



        if risk_distance == 0:

            result.reason = (
                "Invalid risk distance"
            )

            return result



        rr = (
            reward_distance /
            risk_distance
        )

        # ======================================================
        # Maximum RR Cap
        # ======================================================

        if rr > self.maximum_rr:

            if direction == "Bullish":

                target = (
                    entry +
                    risk_distance *
                    self.maximum_rr
                )

            else:

                target = (
                    entry -
                    risk_distance *
                    self.maximum_rr
                )


            reward_distance = abs(
                target - entry
            )


            rr = (
                reward_distance /
                risk_distance
            )

            print(
                    "RISK DEBUG:",
                    "ENTRY=", entry,
                    "SL=", stop_loss,
                    "TARGET=", target,
                    "RR=", round(rr,2)
            )



        # ======================================================
        # RR Validation
        # ======================================================

        if rr < self.minimum_rr:

            result.target = target

            result.reward_amount = reward_distance

            result.risk_amount = (
                self.calculate_risk_amount()
            )

            result.risk_reward = round(
                rr,
                2
            )

            result.valid = False

            result.reason = (
                "Risk reward below minimum"
            )

            return result



        if rr > self.maximum_rr:

            result.target = target

            result.reward_amount = reward_distance

            result.risk_amount = (
                self.calculate_risk_amount()
            )

            result.risk_reward = round(
                rr,
                2
            )

            result.valid = False

            result.reason = (
                "Risk reward above maximum"
            )

            return result



        result.target = target

        result.reward_amount = reward_distance

        result.risk_amount = (
            self.calculate_risk_amount()
        )

        result.risk_reward = round(
            rr,
            2
        )


        result.position_size = round(
            self.calculate_position_size(
                result.risk_amount,
                entry,
                stop_loss
            ),
            2
        )



        result.valid = True

        result.reason = (
            "Valid risk reward setup"
        )


        return result
