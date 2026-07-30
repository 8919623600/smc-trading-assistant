"""
engine/market_engine.py

BMIE Market Engine

Responsibilities
----------------
- Run multi-timeframe market analysis
- Store analysis results
- Print formatted market report
- Display SMC intelligence

Author: BMIE Project
"""


from analyzer import analyze_market
from config import TIMEFRAMES
from models import MarketAnalysis



class MarketEngine:
    """
    Runs the complete BMIE analysis pipeline.
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


        return (
            f"{event.direction} | "
            f"Level: {event.level:.2f} | "
            f"Time: {event.time}"
        )



    # ======================================================
    # Order Block Formatter
    # ======================================================

    @staticmethod
    def print_order_blocks(order_blocks):

        if not order_blocks:

            print(
                "Order Blocks    : None"
            )

            return


        print(
            "Order Blocks"
        )

        print(
            "-" * 60
        )


        for ob in order_blocks:

            print(
                f"Direction       : {ob.direction}"
            )

            print(
                f"High            : {ob.high:.2f}"
            )

            print(
                f"Low             : {ob.low:.2f}"
            )

            print(
                f"Created At      : {ob.created_at}"
            )

            print(
                f"Mitigated       : {ob.mitigated}"
            )

            print(
                f"Broken          : {ob.broken}"
            )

            print(
                f"Strength        : {ob.strength}"
            )

            print()



    # ======================================================
    # Market State Formatter
    # ======================================================

    @staticmethod
    def format_market_state(result):

        if not hasattr(
            result,
            "market_state"
        ):

            return None


        return result.market_state



    # ======================================================
    # Print Report
    # ======================================================

    def print_report(self):

        print(
            "=" * 60
        )


        for section, result in self.analysis.as_dict().items():


            if result is None:

                continue



            print(
                f"\n{section.upper()}"
            )

            print(
                "=" * 60
            )


            print(
                f"Timeframe      : {result.timeframe}"
            )


            print(
                f"Current Price  : {result.current_price:.2f}"
            )


            print(
                f"Current Time   : {result.current_time}"
            )


            print()


            print(
                f"Structure      : {result.structure}"
            )


            if result.market_structure:


                print(
                    f"Trend          : {result.market_structure.trend}"
                )


                print(
                    f"State          : {result.market_structure.state}"
                )



            # ==================================================
            # Market State
            # ==================================================

            market_state = self.format_market_state(
                result
            )


            if market_state:

                print()

                print(
                    f"Market Phase   : {market_state.phase}"
                )


                print(
                    f"Active Event   : {market_state.active_event}"
                )


                print(
                    f"Reason         : {market_state.reason}"
                )



            print()


            print(
                f"BOS            : {self.format_event(result.bos)}"
            )


            print(
                f"CHoCH          : {self.format_event(result.choch)}"
            )



            print()


            # ==================================================
            # Order Blocks
            # ==================================================

            self.print_order_blocks(
                result.order_blocks
            )



            print()


            print(
                f"Confidence     : {result.confidence:.2f}%"
            )



        print(
            "\nBMIE analysis completed."
        )