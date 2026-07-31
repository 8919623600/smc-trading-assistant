"""
journal/trade_journal.py

BMIE Trade Journal V1

Responsibilities
----------------
- Store BMIE analysis history
- Save trade setups
- Save entry confirmations
- Save risk plans
- Prepare dataset for backtesting

Storage:
JSON file

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
    # Create Storage
    # ======================================================

    def create_storage(self):


        directory = os.path.dirname(

            self.file_path

        )



        if directory and not os.path.exists(directory):


            os.makedirs(

                directory

            )





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





    # ======================================================
    # Load Existing Trades
    # ======================================================

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



        trade_data["timestamp"] = (

            datetime.now()

            .strftime(

                "%Y-%m-%d %H:%M:%S"

            )

        )



        trade_data["id"] = (

            len(trades)

            +

            1

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
    # Build BMIE Journal Entry
    # ======================================================

    def create_entry(
        self,
        session,
        analysis,
        setup_quality,
        entry_confirmation,
        risk_plan=None,
    ):



        entry = {}



        entry["symbol"] = (

            session.symbol

        )



        entry["exchange"] = (

            session.exchange

        )





        # -------------------------------
        # Price
        # -------------------------------

        if analysis.entry:


            entry["price"] = (

                analysis.entry.current_price

            )





        # -------------------------------
        # Structure
        # -------------------------------

        entry["market_structure"] = {



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





        # -------------------------------
        # Setup Quality
        # -------------------------------

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





        # -------------------------------
        # Entry Confirmation
        # -------------------------------

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





        # -------------------------------
        # Risk Plan
        # -------------------------------

        if risk_plan:


            entry["risk"] = {


                "entry":

                    risk_plan.entry,


                "stop_loss":

                    risk_plan.stop_loss,


                "target":

                    risk_plan.target,


                "rr":

                    risk_plan.risk_reward,


                "position":

                    risk_plan.position_size

            }





        return entry





    # ======================================================
    # Get Statistics
    # ======================================================

    def count(self):


        trades = self.load_trades()


        return len(trades)