"""
backtest/trade_simulator.py

BMIE Trade Simulator V2

Responsibilities
----------------
- Simulate historical trades
- Accept BMIE StrategyEngine signals
- Check target and stop loss
- Calculate trade results
- Prepare backtest statistics

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

        # BMIE StrategyEngine currently sends
        # TRADE READY signals without direction.
        # Infer direction from target and entry.

        entry = signal.get("entry")
        target = signal.get("target")

        if not direction:

            if target and entry:

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
                signal.get("stop_loss"),

            "target":
                target,

            "risk_reward":
                signal.get("risk_reward", 0),

            "status":
                "OPEN",

            "result":
                "PENDING"

        }


        return trade



    # ======================================================
    # Simulate Trade
    # ======================================================

    def simulate(
        self,
        trade,
        candles
    ):


        entry = trade.get("entry")
        stop_loss = trade.get("stop_loss")
        target = trade.get("target")
        direction = trade.get("direction")


        if not entry or not stop_loss or not target:

            trade["status"] = "INVALID"
            trade["result"] = "NO_RISK_PLAN"

            return trade



        for _, candle in candles.iterrows():

            high = candle["high"]
            low = candle["low"]


            if direction == "BUY":


                if low <= stop_loss:

                    trade["status"] = "CLOSED"
                    trade["result"] = "LOSS"
                    trade["exit_price"] = stop_loss

                    break


                if high >= target:

                    trade["status"] = "CLOSED"
                    trade["result"] = "WIN"
                    trade["exit_price"] = target

                    break



            elif direction == "SELL":


                if high >= stop_loss:

                    trade["status"] = "CLOSED"
                    trade["result"] = "LOSS"
                    trade["exit_price"] = stop_loss

                    break


                if low <= target:

                    trade["status"] = "CLOSED"
                    trade["result"] = "WIN"
                    trade["exit_price"] = target

                    break



        return trade



    # ======================================================
    # Calculate RR
    # ======================================================

    def calculate_rr(
        self,
        trade
    ):

        entry = trade.get("entry")
        stop_loss = trade.get("stop_loss")
        target = trade.get("target")


        if not entry or not stop_loss or not target:

            return 0


        risk = abs(
            entry - stop_loss
        )


        reward = abs(
            target - entry
        )


        if risk == 0:

            return 0


        return round(
            reward / risk,
            2
        )
