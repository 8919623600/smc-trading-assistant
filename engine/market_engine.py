"""
engine/market_engine.py

BMIE Market Engine

Responsibilities
----------------
- Run multi-timeframe market analysis
- Store analysis results
- Print concise trading report
- Display SMC trade decision

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

        if event is None:
            return "None"


        if event.direction is None:
            return "None"


        return event.direction



    # ======================================================
    # Latest Order Block
    # ======================================================

    @staticmethod
    def get_order_block(result):

        if not result.order_blocks:

            return None


        return sorted(
            result.order_blocks,
            key=lambda x: x.created_at,
            reverse=True
        )[0]



    # ======================================================
    # Latest FVG
    # ======================================================

    @staticmethod
    def get_fvg(result):

        if not result.fair_value_gaps:

            return None


        return sorted(
            result.fair_value_gaps,
            key=lambda x: x.created_at,
            reverse=True
        )[0]



    # ======================================================
    # Print Report
    # ======================================================

    def print_report(self):


        print("\n")

        print("=" * 60)
        print("BMIE MARKET INTELLIGENCE REPORT")
        print("=" * 60)


        entry = self.analysis.entry


        print(
            f"Symbol : {self.session.symbol.upper()}"
        )


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

                phase = result.market_state.phase

                event = result.market_state.active_event



            print(
                f"{name.upper():10}: "
                f"{phase} | {event}"
            )



        if entry is None:

            return



        print()

        print("-" * 60)
        print("ACTIVE SETUP")
        print("-" * 60)



        if hasattr(
            entry,
            "market_state"
        ):


            print(
                f"Phase      : "
                f"{entry.market_state.phase}"
            )


            print(
                f"Reason     : "
                f"{entry.market_state.reason}"
            )


        print(
            f"BOS        : "
            f"{self.format_event(entry.bos)}"
        )


        print(
            f"CHoCH      : "
            f"{self.format_event(entry.choch)}"
        )



        # ==================================================
        # Order Block
        # ==================================================

        ob = self.get_order_block(entry)


        print()


        if ob:

            print("Order Block")

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
                "Order Block : None"
            )



        # ==================================================
        # FVG
        # ==================================================

        fvg = self.get_fvg(entry)


        print()


        if fvg:

            print("FVG")

            print(
                f"Type       : {fvg.direction}"
            )

            print(
                f"Zone       : "
                f"{fvg.low:.2f} - {fvg.high:.2f}"
            )

            print(
                f"Filled     : {fvg.filled}"
            )

        else:

            print(
                "FVG        : None"
            )



        # ==================================================
        # Trade Decision
        # ==================================================

        print()

        print("-" * 60)
        print("TRADE DECISION")
        print("-" * 60)



        decision = entry.trade_decision


        if decision:


            print(
                f"Signal     : {decision.signal}"
            )


            print(
                f"Confidence : "
                f"{decision.confidence:.2f}%"
            )


            print()


            print("Reasons:")


            if decision.reasons:


                for reason in decision.reasons:

                    print(
                        f"- {reason}"
                    )


            else:

                print(
                    "- No confirmation"
                )


        else:

            print(
                "No decision generated"
            )



        print("=" * 60)

        print(
            "BMIE analysis completed."
        )