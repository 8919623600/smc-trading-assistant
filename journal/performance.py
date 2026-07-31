"""
journal/performance.py

BMIE Performance Analytics V2

Responsibilities
----------------
- Analyze BMIE journal data
- Track setup quality performance
- Track trade lifecycle
- Calculate confidence statistics
- Prepare data for backtesting

Author: BMIE Project
"""


import json
import os
from collections import Counter





class PerformanceAnalyzer:


    def __init__(
        self,
        file_path="journal/trades.json"
    ):

        self.file_path = file_path





    # ======================================================
    # Load Trades
    # ======================================================

    def load_trades(self):


        if not os.path.exists(
            self.file_path
        ):

            return []



        try:


            with open(
                self.file_path,
                "r"
            ) as file:


                return json.load(file)



        except Exception:


            return []





    # ======================================================
    # Total Trades
    # ======================================================

    def total_trades(self):


        return len(

            self.load_trades()

        )





    # ======================================================
    # Trade Status
    # ======================================================

    def trade_status(self):


        result = {


            "OPEN": 0,

            "CLOSED": 0,

            "PENDING": 0


        }



        for trade in self.load_trades():


            status = trade.get(

                "status",

                "PENDING"

            )



            if status in result:


                result[status] += 1



            else:


                result["PENDING"] += 1





        return result





    # ======================================================
    # Result Analysis
    # ======================================================

    def result_analysis(self):


        result = {


            "WIN": 0,

            "LOSS": 0,

            "PENDING": 0


        }



        for trade in self.load_trades():


            outcome = trade.get(

                "result",

                "PENDING"

            )



            if outcome in result:


                result[outcome] += 1



            else:


                result["PENDING"] += 1





        return result





    # ======================================================
    # Grade Analysis
    # ======================================================

    def grade_analysis(self):


        grades = []



        for trade in self.load_trades():


            quality = trade.get(

                "setup_quality",

                {}

            )



            grades.append(

                quality.get(

                    "grade",

                    "UNKNOWN"

                )

            )



        return dict(

            Counter(

                grades

            )

        )





    # ======================================================
    # Average Confidence
    # ======================================================

    def average_confidence(self):


        values = []



        for trade in self.load_trades():


            confirmation = trade.get(

                "entry_confirmation",

                {}

            )



            confidence = confirmation.get(

                "confidence"

            )



            if confidence is not None:


                values.append(

                    float(confidence)

                )





        if not values:


            return 0





        return round(

            sum(values)

            /

            len(values),

            2

        )





    # ======================================================
    # Average Risk Reward
    # ======================================================

    def average_rr(self):


        values = []



        for trade in self.load_trades():


            plan = trade.get(

                "trade_plan",

                {}

            )



            rr = plan.get(

                "risk_reward"

            )



            if rr is not None:


                values.append(

                    float(rr)

                )





        if not values:


            return 0





        return round(

            sum(values)

            /

            len(values),

            2

        )





    # ======================================================
    # Generate Report
    # ======================================================

    def generate_report(self):


        return {


            "total":

                self.total_trades(),


            "status":

                self.trade_status(),


            "results":

                self.result_analysis(),


            "grades":

                self.grade_analysis(),


            "average_confidence":

                self.average_confidence(),


            "average_rr":

                self.average_rr()


        }





    # ======================================================
    # Print Report
    # ======================================================

    def print_report(self):


        report = self.generate_report()



        print("=" * 60)

        print(

            "BMIE PERFORMANCE REPORT V2"

        )

        print("=" * 60)



        print()

        print(

            f"Total Setups: {report['total']}"

        )



        print()

        print(

            "Trade Status"

        )



        for key, value in report["status"].items():


            print(

                f"{key}: {value}"

            )



        print()

        print(

            "Results"

        )



        for key, value in report["results"].items():


            print(

                f"{key}: {value}"

            )



        print()

        print(

            "Grade Distribution"

        )



        for key, value in report["grades"].items():


            print(

                f"{key}: {value}"

            )



        print()

        print(

            f"Average Confidence: "

            f"{report['average_confidence']}%"

        )



        print(

            f"Average RR: "

            f"{report['average_rr']}"

        )



        print("=" * 60)





if __name__ == "__main__":


    analyzer = PerformanceAnalyzer()


    analyzer.print_report()