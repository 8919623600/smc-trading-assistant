"""
engine/market_engine.py

BMIE Market Engine

Responsibilities
----------------
- Run multi-timeframe market analysis
- Store analysis results
- Print concise trading report

Author: BMIE Project
"""


from analyzer import analyze_market
from config import TIMEFRAMES
from models import MarketAnalysis


class MarketEngine:
    """
    Runs BMIE analysis pipeline.
    """


    def __init__(self, session):

        self.session = session

        self.analysis = MarketAnalysis()



    # ======================================================
    # Run Analysis
    # ======================================================

    def run(self):

        print("\nRunning Multi-Timeframe Analysis...")
        print("-" * 60)


        for name, timeframe in TIMEFRAMES.items():

            print(
                f"Analyzing {name.upper()} ({timeframe})..."
            )


            result = analyze_market(
                self.session,
                timeframe,
            )


            setattr(
                self.analysis,
                name,
                result
            )


        print(
            "\nAnalysis Completed Successfully."
        )



    # ======================================================
    # Event Formatter
    # ======================================================

    @staticmethod
    def format_event(event):

        if event.direction is None:

            return "None"


        return event.direction



    # ======================================================
    # Order Block Formatter
    # ======================================================

    @staticmethod
    def get_best_order_block(result):

        if not result.order_blocks:

            return None


        # Latest order block
        return sorted(
            result.order_blocks,
            key=lambda x: x.created_at,
            reverse=True
        )[0]



    # ======================================================
    # Short Report
    # ======================================================

    def print_report(self):

        print("\n")
        print("=" * 60)
        print("BMIE MARKET INTELLIGENCE REPORT")
        print("=" * 60)


        print(
            f"Symbol : {self.session.symbol}"
        )


        # Current price from entry timeframe

        entry = self.analysis.entry


        if entry:

            print(
                f"Price  : {entry.current_price:.2f}"
            )


        print()
        print("-" * 60)
        print("MULTI TIMEFRAME STRUCTURE")
        print("-" * 60)



        for name, result in self.analysis.as_dict().items():

            if result is None:

                continue


            phase = "Unknown"

            event = "None"


            if hasattr(
                result,
                "market_state"
            ):

                phase = (
                    result.market_state.phase
                )

                event = (
                    result.market_state.active_event
                )


            print(
                f"{name.upper():6} : "
                f"{phase} | {event}"
            )



        print()
        print("-" * 60)
        print("ACTIVE SETUP")
        print("-" * 60)



        trend = "Unknown"

        if entry and entry.market_structure:

            trend = (
                entry.market_structure.trend
            )


        print(
            f"Trend      : {trend}"
        )


        if entry:

            print(
                f"CHoCH      : "
                f"{self.format_event(entry.choch)}"
            )


            print(
                f"BOS        : "
                f"{self.format_event(entry.bos)}"
            )



        # ==================================================
        # Order Block
        # ==================================================

        if entry:

            ob = self.get_best_order_block(
                entry
            )


            if ob:

                print()

                print(
                    "Order Block"
                )

                print(
                    f"Type       : {ob.direction}"
                )

                print(
                    f"Zone       : "
                    f"{ob.low:.2f} - {ob.high:.2f}"
                )

                print(
                    f"Time       : {ob.created_at}"
                )


            else:

                print(
                    "Order Block: None"
                )



        print()
        print("-" * 60)
        print("TRADE BIAS")
        print("-" * 60)



        if entry and entry.market_state:

            if (
                entry.market_state.phase
                == "Bullish Continuation"
            ):

                print(
                    "Direction  : BUY"
                )


            elif (
                entry.market_state.phase
                == "Bearish Continuation"
            ):

                print(
                    "Direction  : SELL"
                )


            else:

                print(
                    "Direction  : WAIT"
                )


        print(
            "Confidence : Pending"
        )


        print("=" * 60)

        print(
            "BMIE analysis completed."
        )