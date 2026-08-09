"""
smc/risk_manager.py

BMIE Risk Manager V5.2 Compatibility

Purpose
-------
- Preserve BMIE V4 working flow
- Support BMIE entry confirmation flow
- Add entry zone support
- Add RR ceiling
- Improve validation
- Improve direction detection

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





    # ======================================================
    # Risk Amount
    # ======================================================

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


        # ------------------------------------------
        # Signal based detection
        # ------------------------------------------

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





        # ------------------------------------------
        # Direct direction field
        # ------------------------------------------

        direction = getattr(

            trade_decision,

            "direction",

            None

        )



        if direction:


            direction = str(

                direction

            ).upper()



            if "BUY" in direction:

                return "Bullish"



            if "SELL" in direction:

                return "Bearish"





        # ------------------------------------------
        # Analysis direction fallback
        # ------------------------------------------

        analysis = getattr(

            trade_decision,

            "analysis",

            None

        )



        if analysis:


            direction = getattr(

                analysis,

                "direction",

                None

            )



            if direction:


                direction = str(

                    direction

                ).upper()



                if "BULL" in direction:

                    return "Bullish"



                if "BEAR" in direction:

                    return "Bearish"





        return None





    # ======================================================
    # Entry Calculation
    # ======================================================

    def calculate_entry(
        self,
        trade_decision,
        order_blocks
    ):


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


                return (

                    high + low

                ) / 2





        return getattr(

            trade_decision,

            "price",

            None

        )





    # ======================================================
    # Entry Zone
    # ======================================================

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





    # ======================================================
    # Stop Loss
    # ======================================================

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





    # ======================================================
    # Target
    # ======================================================

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





    # ======================================================
    # Position Size
    # ======================================================

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



        return risk_amount / distance





    # ======================================================
    # Analyze Risk
    # ======================================================

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


            result.reason = (

                "Direction unavailable"

            )


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



        entry_low, entry_high = self.calculate_entry_zone(

            order_blocks

        )





        result.direction = direction

        result.entry = entry

        result.entry_low = entry_low

        result.entry_high = entry_high

        result.stop_loss = stop_loss

        result.target = target





        if entry is None:


            result.reason = "Entry unavailable"

            return result





        if stop_loss is None:


            result.reason = "Stop loss unavailable"

            return result





        if target is None:


            result.reason = "Target unavailable"

            return result





        risk_distance = abs(

            entry - stop_loss

        )



        reward_distance = abs(

            target - entry

        )



        if risk_distance == 0:


            result.reason = "Invalid risk distance"

            return result





        rr = (

            reward_distance /

            risk_distance

        )





        # RR ceiling

        if rr > self.maximum_rr:


            if direction == "Bullish":


                target = (

                    entry +

                    (

                        risk_distance *

                        self.maximum_rr

                    )

                )


            else:


                target = (

                    entry -

                    (

                        risk_distance *

                        self.maximum_rr

                    )

                )



            reward_distance = abs(

                target - entry

            )



            rr = (

                reward_distance /

                risk_distance

            )





        result.target = target


        result.reward_amount = reward_distance


        result.risk_amount = self.calculate_risk_amount()


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





        if rr >= self.minimum_rr:


            result.valid = True

            result.reason = (

                "Valid risk reward setup"

            )


        else:


            result.valid = False

            result.reason = (

                "Risk reward below minimum"

            )





        return result