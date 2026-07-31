"""
monitor/trade_monitor.py

BMIE Trade Monitor V1

Responsibilities
----------------
- Monitor active trades
- Compare current price with SL/TP
- Return trade status
- Prepare journal updates

Author: BMIE Project
"""


class TradeMonitor:


    def __init__(self):

        pass



    # ======================================================
    # Check Trade Status
    # ======================================================

    def check_trade(
        self,
        trade,
        current_price
    ):


        result = {

            "status": "OPEN",

            "result": "PENDING",

            "current_price": current_price

        }



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
            "direction",
            ""
        ).upper()



        if not entry or not stop_loss or not target:

            result["status"] = "INVALID"

            result["result"] = "NO_RISK_PLAN"

            return result





        # ==================================================
        # BUY Trade
        # ==================================================

        if direction == "BUY":


            if current_price >= target:

                result["status"] = "CLOSED"

                result["result"] = "WIN"



            elif current_price <= stop_loss:

                result["status"] = "CLOSED"

                result["result"] = "LOSS"





        # ==================================================
        # SELL Trade
        # ==================================================

        elif direction == "SELL":


            if current_price <= target:

                result["status"] = "CLOSED"

                result["result"] = "WIN"



            elif current_price >= stop_loss:

                result["status"] = "CLOSED"

                result["result"] = "LOSS"





        return result





    # ======================================================
    # Calculate Progress
    # ======================================================

    def calculate_progress(
        self,
        trade,
        current_price
    ):


        entry = trade.get(
            "entry"
        )


        target = trade.get(
            "target"
        )


        if not entry or not target:

            return 0



        total_distance = abs(

            target - entry

        )


        current_distance = abs(

            current_price - entry

        )


        if total_distance == 0:

            return 0



        return round(

            (

                current_distance /

                total_distance

            )

            *

            100,

            2

        )