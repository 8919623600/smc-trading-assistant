"""
backtest/trade_simulator.py

BMIE Trade Simulator V1

Responsibilities
----------------
- Simulate historical trades
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


        trade = {


            "symbol":

                signal.get(
                    "symbol"
                ),


            "time":

                signal.get(
                    "time"
                ),


            "direction":

                signal.get(
                    "direction",
                    "BUY"
                ),


            "entry":

                signal.get(
                    "entry"
                ),


            "stop_loss":

                signal.get(
                    "stop_loss"
                ),


            "target":

                signal.get(
                    "target"
                ),


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



        if not entry or not stop_loss or not target:


            trade["status"] = "INVALID"

            trade["result"] = "NO_RISK_PLAN"

            return trade





        for _, candle in candles.iterrows():


            high = candle["high"]

            low = candle["low"]



            # ==============================================
            # BUY Trade
            # ==============================================

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





            # ==============================================
            # SELL Trade
            # ==============================================

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


        entry = trade.get(
            "entry"
        )


        stop_loss = trade.get(
            "stop_loss"
        )


        target = trade.get(
            "target"
        )



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