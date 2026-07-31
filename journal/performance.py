"""
journal/performance.py

BMIE Performance Analytics V1

Responsibilities
----------------
- Read BMIE journal data
- Calculate setup statistics
- Analyze grades
- Analyze entry confirmations
- Calculate average confidence

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
    # Total Analysis
    # ======================================================

    def total_trades(self):


        return len(

            self.load_trades()

        )





    # ======================================================
    # Grade Distribution
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
    # Entry Confirmation Statistics
    # ======================================================

    def entry_confirmation_analysis(self):


        result = {


            "ENTRY CONFIRMED": 0,


            "WAIT FOR CONFIRMATION": 0,


            "OTHER": 0


        }



        for trade in self.load_trades():


            confirmation = trade.get(

                "entry_confirmation",

                {}

            )



            status = confirmation.get(

                "status",

                "OTHER"

            )



            if status in result:


                result[status] += 1



            else:


                result["OTHER"] += 1





        return result





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

            sum(values) / len(values),

            2

        )





    # ======================================================
    # Generate Report
    # ======================================================

    def generate_report(self):


        return {


            "total_analysis":

                self.total_trades(),



            "grade_distribution":

                self.grade_analysis(),



            "entry_confirmation":

                self.entry_confirmation_analysis(),



            "average_confidence":

                self.average_confidence()


        }





    # ======================================================
    # Print Report
    # ======================================================

    def print_report(self):


        report = self.generate_report()



        print("=" * 60)

        print(

            "BMIE PERFORMANCE REPORT"

        )

        print("=" * 60)



        print()



        print(

            f"Total Analysis: "

            f"{report['total_analysis']}"

        )



        print()



        print(

            "Grade Distribution:"

        )



        for grade, count in report[

            "grade_distribution"

        ].items():


            print(

                f"{grade}: {count}"

            )





        print()



        print(

            "Entry Confirmation:"

        )



        for status, count in report[

            "entry_confirmation"

        ].items():


            print(

                f"{status}: {count}"

            )





        print()



        print(

            f"Average Confidence: "

            f"{report['average_confidence']}%"

        )



        print("=" * 60)





if __name__ == "__main__":


    analyzer = PerformanceAnalyzer()


    analyzer.print_report()