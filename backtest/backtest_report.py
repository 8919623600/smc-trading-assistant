"""
backtest/backtest_report.py

BMIE Backtest Report V1

Responsibilities
----------------
- Analyze simulated trades
- Generate performance statistics
- Print backtest summary

Author: BMIE Project
"""


from collections import Counter





class BacktestReport:


    def __init__(
        self,
        trades
    ):

        self.trades = trades





    # ======================================================
    # Total Trades
    # ======================================================

    def total_trades(self):

        return len(
            self.trades
        )





    # ======================================================
    # Result Analysis
    # ======================================================

    def result_analysis(self):


        result = {


            "WIN": 0,

            "LOSS": 0,

            "PENDING": 0,

            "INVALID": 0


        }



        for trade in self.trades:


            status = trade.get(

                "result",

                "PENDING"

            )



            if status in result:


                result[status] += 1


            else:


                result["PENDING"] += 1



        return result





    # ======================================================
    # Win Rate
    # ======================================================

    def win_rate(self):


        results = self.result_analysis()



        total_closed = (

            results["WIN"]

            +

            results["LOSS"]

        )



        if total_closed == 0:

            return 0



        return round(

            (

                results["WIN"]

                /

                total_closed

            )

            *

            100,

            2

        )





    # ======================================================
    # Average RR
    # ======================================================

    def average_rr(self):


        values = []



        for trade in self.trades:


            rr = trade.get(

                "rr"

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
    # Grade Analysis
    # ======================================================

    def grade_analysis(self):


        grades = []



        for trade in self.trades:


            grade = trade.get(

                "grade",

                "UNKNOWN"

            )


            grades.append(

                grade

            )



        return dict(

            Counter(

                grades

            )

        )





    # ======================================================
    # Generate Report
    # ======================================================

    def generate(self):


        results = self.result_analysis()



        return {


            "total_trades":

                self.total_trades(),


            "results":

                results,


            "win_rate":

                self.win_rate(),


            "average_rr":

                self.average_rr(),


            "grades":

                self.grade_analysis()


        }





    # ======================================================
    # Print Report
    # ======================================================

    def print_report(self):


        report = self.generate()



        print("=" * 60)

        print(

            "BMIE BACKTEST REPORT V1"

        )

        print("=" * 60)



        print()


        print(

            f"Total Trades: "

            f"{report['total_trades']}"

        )



        print()


        print(

            "Trade Results"

        )


        for key, value in report["results"].items():


            print(

                f"{key}: {value}"

            )



        print()


        print(

            f"Win Rate: "

            f"{report['win_rate']}%"

        )


        print(

            f"Average RR: "

            f"{report['average_rr']}"

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


        print("=" * 60)





if __name__ == "__main__":


    report = BacktestReport([])

    report.print_report()