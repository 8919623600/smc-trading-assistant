"""
journal/trade_journal.py

BMIE Trade Journal V2

Responsibilities
----------------
- Store BMIE analysis history
- Store trade lifecycle
- Track OPEN/WIN/LOSS status
- Prepare data for performance analysis

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



    def create_storage(self):

        directory = os.path.dirname(
            self.file_path
        )

        if directory and not os.path.exists(directory):

            os.makedirs(directory)


        if not os.path.exists(self.file_path):

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



    def save_trade(
        self,
        trade_data
    ):

        trades = self.load_trades()


        trade_data["id"] = len(trades) + 1

        trade_data["timestamp"] = (
            datetime.now()
            .strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )


        if "status" not in trade_data:

            trade_data["status"] = "OPEN"


        if "result" not in trade_data:

            trade_data["result"] = "PENDING"


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



    def update_trade_result(
        self,
        trade_id,
        result,
        exit_price,
        profit_loss
    ):

        trades = self.load_trades()


        for trade in trades:

            if trade.get("id") == trade_id:

                trade["result"] = result

                trade["status"] = (
                    "CLOSED"
                )

                trade["exit_price"] = exit_price

                trade["profit_loss"] = profit_loss



        with open(
            self.file_path,
            "w"
        ) as file:

            json.dump(
                trades,
                file,
                indent=4
            )


    def create_entry(
        self,
        session,
        analysis,
        setup_quality,
        entry_confirmation,
        risk_plan=None
    ):

        entry = {}


        entry["symbol"] = (
            session.symbol
        )

        entry["exchange"] = (
            session.exchange
        )


        entry["timestamp"] = (
            datetime.now()
            .strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )


        entry["market_structure"] = {

            "bias": str(
                analysis.bias
            ),

            "structure": str(
                analysis.structure
            ),

            "trend": str(
                analysis.trend
            ),

            "setup": str(
                analysis.setup
            ),

            "entry": str(
                analysis.entry
            )

        }


        if setup_quality:

            entry["setup_quality"] = {

                "score": setup_quality.score,

                "grade": setup_quality.grade,

                "strengths": setup_quality.strengths,

                "warnings": setup_quality.warnings

            }


        if entry_confirmation:

            entry["entry_confirmation"] = {

                "status": entry_confirmation.get(
                    "status"
                ),

                "confidence": entry_confirmation.get(
                    "confidence"
                ),

                "reasons": entry_confirmation.get(
                    "reasons"
                )

            }


        if risk_plan:

            entry["trade_plan"] = {

                "direction": risk_plan.direction,

                "entry": risk_plan.entry,

                "stop_loss": risk_plan.stop_loss,

                "target": risk_plan.target,

                "risk_reward": risk_plan.risk_reward,

                "position_size": risk_plan.position_size

            }


        entry["status"] = "OPEN"

        entry["result"] = "PENDING"

        entry["exit_price"] = None

        entry["profit_loss"] = None


        return entry
