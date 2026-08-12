"""
backtest/trade_simulator.py

BMIE Trade Simulator V3

Responsibilities
----------------
- Simulate historical trades
- Accept BMIE StrategyEngine signals
- Wait for actual entry price
- Activate trade only after entry is touched
- Check target and stop loss after activation
- Calculate trade results
- Calculate RR
- Prepare basic backtest statistics

Author: BMIE Project
"""


class TradeSimulator:


    def __init__(self):
        pass


    # ======================================================
    # Create Trade
    # ======================================================

    def create_trade(
        self,
        signal
    ):

        direction = signal.get(
            "direction"
        )

        entry = signal.get(
            "entry"
        )

        target = signal.get(
            "target"
        )

        stop_loss = signal.get(
            "stop_loss"
        )


        # --------------------------------------------------
        # Infer direction only when missing
        # --------------------------------------------------

        if not direction:

            if (
                entry is not None
                and
                target is not None
            ):

                direction = (
                    "BUY"
                    if target > entry
                    else "SELL"
                )

            else:

                direction = "BUY"


        trade = {

            "symbol":
                signal.get("symbol"),

            "time":
                signal.get("time"),

            "direction":
                direction,

            "entry":
                entry,

            "stop_loss":
                stop_loss,

            "target":
                target,

            "risk_reward":
                signal.get(
                    "risk_reward",
                    0
                ),

            "status":
                "WAITING_FOR_ENTRY",

            "result":
                "PENDING",

            "entry_triggered":
                False,

            "entry_time":
                None,

            "exit_time":
                None,

            "exit_price":
                None

        }


        return trade


    # ======================================================
    # Entry Check
    # ======================================================

    def check_entry_trigger(
        self,
        trade,
        candle
    ):

        entry = trade.get(
            "entry"
        )

        if entry is None:
            return False


        high = float(
            candle["high"]
        )

        low = float(
            candle["low"]
        )


        # Entry price was traded during candle

        if (
            low <= entry <= high
        ):

            return True


        return False


    # ======================================================
    # Simulate Trade
    # ======================================================

    def simulate(
        self,
        trade,
        candles
    ):

        entry = trade.get(
            "entry"
        )

        stop_loss = trade.get(
            "stop_loss"
        )

        target = trade.get(
            "target"
        )

        direction = trade.get(
            "direction"
        )


        # --------------------------------------------------
        # Validate risk plan
        # --------------------------------------------------

        if (
            entry is None
            or
            stop_loss is None
            or
            target is None
        ):

            trade["status"] = "INVALID"

            trade["result"] = (
                "NO_RISK_PLAN"
            )

            return trade


        # --------------------------------------------------
        # Validate direction
        # --------------------------------------------------

        if direction not in [
            "BUY",
            "SELL"
        ]:

            trade["status"] = "INVALID"

            trade["result"] = (
                "INVALID_DIRECTION"
            )

            return trade


        # --------------------------------------------------
        # Start waiting for entry
        # --------------------------------------------------

        trade["status"] = (
            "WAITING_FOR_ENTRY"
        )

        trade["result"] = (
            "PENDING"
        )


        for _, candle in candles.iterrows():

            high = float(
                candle["high"]
            )

            low = float(
                candle["low"]
            )


            candle_time = (
                candle["time"]
                if "time" in candle
                else None
            )


            # ==================================================
            # STEP 1
            # Wait until price reaches entry
            # ==================================================

            if not trade["entry_triggered"]:


                if not self.check_entry_trigger(
                    trade,
                    candle
                ):

                    continue


                # Entry has now been triggered

                trade["entry_triggered"] = True

                trade["status"] = (
                    "OPEN"
                )

                trade["entry_time"] = (
                    candle_time
                )


                # --------------------------------------------------
                # If entry candle also reaches SL/TP,
                # evaluate it conservatively.
                #
                # When both are touched in the same OHLC candle,
                # exact intrabar order is unknowable.
                # We treat SL first for a conservative backtest.
                # --------------------------------------------------

                if direction == "BUY":

                    hit_stop = (
                        low <= stop_loss
                    )

                    hit_target = (
                        high >= target
                    )


                    if (
                        hit_stop
                        and
                        hit_target
                    ):

                        trade["status"] = (
                            "CLOSED"
                        )

                        trade["result"] = (
                            "LOSS"
                        )

                        trade["exit_price"] = (
                            stop_loss
                        )

                        trade["exit_time"] = (
                            candle_time
                        )

                        break


                    if hit_stop:

                        trade["status"] = (
                            "CLOSED"
                        )

                        trade["result"] = (
                            "LOSS"
                        )

                        trade["exit_price"] = (
                            stop_loss
                        )

                        trade["exit_time"] = (
                            candle_time
                        )

                        break


                    if hit_target:

                        trade["status"] = (
                            "CLOSED"
                        )

                        trade["result"] = (
                            "WIN"
                        )

                        trade["exit_price"] = (
                            target
                        )

                        trade["exit_time"] = (
                            candle_time
                        )

                        break


                elif direction == "SELL":

                    hit_stop = (
                        high >= stop_loss
                    )

                    hit_target = (
                        low <= target
                    )


                    if (
                        hit_stop
                        and
                        hit_target
                    ):

                        trade["status"] = (
                            "CLOSED"
                        )

                        trade["result"] = (
                            "LOSS"
                        )

                        trade["exit_price"] = (
                            stop_loss
                        )

                        trade["exit_time"] = (
                            candle_time
                        )

                        break


                    if hit_stop:

                        trade["status"] = (
                            "CLOSED"
                        )

                        trade["result"] = (
                            "LOSS"
                        )

                        trade["exit_price"] = (
                            stop_loss
                        )

                        trade["exit_time"] = (
                            candle_time
                        )

                        break


                    if hit_target:

                        trade["status"] = (
                            "CLOSED"
                        )

                        trade["result"] = (
                            "WIN"
                        )

                        trade["exit_price"] = (
                            target
                        )

                        trade["exit_time"] = (
                            candle_time
                        )

                        break


                continue


            # ==================================================
            # STEP 2
            # Trade is already open
            # ==================================================

            if direction == "BUY":

                hit_stop = (
                    low <= stop_loss
                )

                hit_target = (
                    high >= target
                )


                # Conservative handling when both
                # are inside the same candle.

                if (
                    hit_stop
                    and
                    hit_target
                ):

                    trade["status"] = (
                        "CLOSED"
                    )

                    trade["result"] = (
                        "LOSS"
                    )

                    trade["exit_price"] = (
                        stop_loss
                    )

                    trade["exit_time"] = (
                        candle_time
                    )

                    break


                if hit_stop:

                    trade["status"] = (
                        "CLOSED"
                    )

                    trade["result"] = (
                        "LOSS"
                    )

                    trade["exit_price"] = (
                        stop_loss
                    )

                    trade["exit_time"] = (
                        candle_time
                    )

                    break


                if hit_target:

                    trade["status"] = (
                        "CLOSED"
                    )

                    trade["result"] = (
                        "WIN"
                    )

                    trade["exit_price"] = (
                        target
                    )

                    trade["exit_time"] = (
                        candle_time
                    )

                    break


            elif direction == "SELL":

                hit_stop = (
                    high >= stop_loss
                )

                hit_target = (
                    low <= target
                )


                if (
                    hit_stop
                    and
                    hit_target
                ):

                    trade["status"] = (
                        "CLOSED"
                    )

                    trade["result"] = (
                        "LOSS"
                    )

                    trade["exit_price"] = (
                        stop_loss
                    )

                    trade["exit_time"] = (
                        candle_time
                    )

                    break


                if hit_stop:

                    trade["status"] = (
                        "CLOSED"
                    )

                    trade["result"] = (
                        "LOSS"
                    )

                    trade["exit_price"] = (
                        stop_loss
                    )

                    trade["exit_time"] = (
                        candle_time
                    )

                    break


                if hit_target:

                    trade["status"] = (
                        "CLOSED"
                    )

                    trade["result"] = (
                        "WIN"
                    )

                    trade["exit_price"] = (
                        target
                    )

                    trade["exit_time"] = (
                        candle_time
                    )

                    break


        # --------------------------------------------------
        # Future candles exhausted
        # --------------------------------------------------

        if trade["entry_triggered"]:

            if trade["status"] != "CLOSED":

                trade["status"] = (
                    "OPEN"
                )

                trade["result"] = (
                    "OPEN"
                )

        else:

            trade["status"] = (
                "NO_ENTRY"
            )

            trade["result"] = (
                "NO_ENTRY"
            )


        return trade


    # ======================================================
    # Calculate RR
    # ======================================================

    def calculate_rr(
        self,
        trade
    ):

        entry = trade.get(
            "entry"
        )

        stop_loss = trade.get(
            "stop_loss"
        )

        target = trade.get(
            "target"
        )


        if (
            entry is None
            or
            stop_loss is None
            or
            target is None
        ):

            return 0


        risk = abs(
            entry -
            stop_loss
        )


        reward = abs(
            target -
            entry
        )


        if risk == 0:

            return 0


        return round(
            reward / risk,
            2
        )