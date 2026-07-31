"""
journal/trade_journal.py

BMIE Trade Journal V3

Responsibilities
----------------
- Store BMIE analysis history
- Store complete signal snapshot
- Track trade lifecycle
- Prepare dataset for backtesting

Author: BMIE Project
"""


import json
import os
from datetime import datetime





class TradeJournal:


    def __init__(
        self,
        file_path="journal/trades.json"
    ):

        self.file_path = file_path

        self.create_storage()





    # ======================================================
    # Storage
    # ======================================================

    def create_storage(self):


        directory = os.path.dirname(

            self.file_path

        )


        if directory and not os.path.exists(directory):

            os.makedirs(directory)



        if not os.path.exists(

            self.file_path

        ):


            with open(

                self.file_path,

                "w"

            ) as file:


                json.dump(

                    [],

                    file,

                    indent=4

                )





    def load_trades(self):


        try:


            with open(

                self.file_path,

                "r"

            ) as file:


                return json.load(file)



        except Exception:


            return []





    # ======================================================
    # Save Trade
    # ======================================================

    def save_trade(
        self,
        trade_data
    ):


        trades = self.load_trades()



        trade_data["id"] = (

            len(trades)

            +

            1

        )


        trade_data["timestamp"] = (

            datetime.now()

            .strftime(

                "%Y-%m-%d %H:%M:%S"

            )

        )


        trade_data.setdefault(

            "status",

            "OPEN"

        )


        trade_data.setdefault(

            "result",

            "PENDING"

        )


        trades.append(

            trade_data

        )



        with open(

            self.file_path,

            "w"

        ) as file:


            json.dump(

                trades,

                file,

                indent=4

            )



        return trade_data





    # ======================================================
    # Create BMIE Snapshot
    # ======================================================

    def create_entry(
        self,
        session,
        analysis,
        setup_quality,
        entry_confirmation,
        trade_decision=None,
        risk_plan=None
    ):


        entry = {}



        entry["symbol"] = (

            session.symbol

        )


        entry["exchange"] = (

            session.exchange

        )



        entry["time"] = (

            datetime.now()

            .strftime(

                "%Y-%m-%d %H:%M:%S"

            )

        )





        # ------------------------------
        # Market Context
        # ------------------------------

        entry["market_context"] = {


            "bias":

                str(analysis.bias),


            "structure":

                str(analysis.structure),


            "trend":

                str(analysis.trend),


            "setup":

                str(analysis.setup),


            "entry":

                str(analysis.entry)

        }





        # ------------------------------
        # Setup Quality
        # ------------------------------

        if setup_quality:


            entry["setup_quality"] = {


                "score":

                    setup_quality.score,


                "grade":

                    setup_quality.grade,


                "strengths":

                    setup_quality.strengths,


                "warnings":

                    setup_quality.warnings

            }





        # ------------------------------
        # Signal Snapshot
        # ------------------------------

        if trade_decision:


            entry["signal"] = {


                "type":

                    trade_decision.signal,


                "confidence":

                    trade_decision.confidence,


                "reasons":

                    trade_decision.reasons

            }





        # ------------------------------
        # Entry Confirmation
        # ------------------------------

        if entry_confirmation:


            entry["entry_confirmation"] = {


                "status":

                    entry_confirmation.get(

                        "status"

                    ),


                "confidence":

                    entry_confirmation.get(

                        "confidence"

                    ),


                "reasons":

                    entry_confirmation.get(

                        "reasons"

                    )

            }





        # ------------------------------
        # Risk Plan
        # ------------------------------

        if risk_plan:


            entry["risk"] = {


                "direction":

                    risk_plan.direction,


                "entry":

                    risk_plan.entry,


                "stop_loss":

                    risk_plan.stop_loss,


                "target":

                    risk_plan.target,


                "rr":

                    risk_plan.risk_reward

            }



        else:


            entry["risk"] = {


                "direction": None,


                "entry": None,


                "stop_loss": None,


                "target": None,


                "rr": None

            }





        # ------------------------------
        # Result Tracking
        # ------------------------------

        entry["result"] = {


            "status":

                "PENDING",


            "exit_price":

                None,


            "profit_loss":

                None

        }



        return entry





    # ======================================================
    # Update Result
    # ======================================================

    def update_result(
        self,
        trade_id,
        status,
        exit_price,
        profit_loss
    ):


        trades = self.load_trades()



        for trade in trades:


            if trade.get("id") == trade_id:


                trade["result"] = {


                    "status":

                        status,


                    "exit_price":

                        exit_price,


                    "profit_loss":

                        profit_loss

                }



                trade["status"] = "CLOSED"





        with open(

            self.file_path,

            "w"

        ) as file:


            json.dump(

                trades,

                file,

                indent=4

            )