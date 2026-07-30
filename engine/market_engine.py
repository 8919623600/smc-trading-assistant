"""
engine/market_engine.py

BMIE Market Engine

Responsibilities
----------------
- Run multi-timeframe analysis
- Build MTF context
- Generate trade decision
- Print concise market report
- Display risk plan

Author: BMIE Project
"""


from analyzer import analyze_market

from config import TIMEFRAMES

from models import (
    MarketAnalysis,
    MultiTimeframeContext,
)

from smc.confluence import ConfluenceEngine



class MarketEngine:


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


        # ==================================================
        # Multi Timeframe Confluence
        # ==================================================

        context = MultiTimeframeContext(

            bias=self.analysis.bias,

            structure=self.analysis.structure,

            trend=self.analysis.trend,

            setup=self.analysis.setup,

            entry=self.analysis.entry,
        )



        confluence_engine = ConfluenceEngine(
            context
        )


        decision = confluence_engine.analyze()



        # Attach decision to entry timeframe

        if self.analysis.entry:

            self.analysis.entry.trade_decision = decision



    # ======================================================
    # Helpers
    # ======================================================

    @staticmethod
    def format_event(event):

        if event is None:

            return "None"


        if event.direction is None:

            return "None"


        return event.direction



    @staticmethod
    def latest_order_block(result):

        if not result:

            return None


        if not result.order_blocks:

            return None



        return sorted(

            result.order_blocks,

            key=lambda x: x.created_at,

            reverse=True

        )[0]



    @staticmethod
    def latest_fvg(result):

        if not result:

            return None


        if not result.fair_value_gaps:

            return None



        return sorted(

            result.fair_value_gaps,

            key=lambda x: x.created_at,

            reverse=True

        )[0]



    # ======================================================
    # Report
    # ======================================================

    def print_report(self):


        entry = self.analysis.entry



        print("\n")

        print("=" * 60)

        print("BMIE MARKET INTELLIGENCE REPORT")

        print("=" * 60)



        print(
            f"Symbol : {self.session.symbol}"
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



            if hasattr(result, "market_state"):


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



        if hasattr(entry, "market_state"):


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



        ob = self.latest_order_block(entry)



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



        fvg = self.latest_fvg(entry)



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



            for reason in decision.reasons:


                print(

                    f"- {reason}"

                )


        else:


            print(

                "Decision unavailable"

            )



        # ==================================================
        # Risk Plan
        # ==================================================

        print()


        print("-" * 60)

        print("RISK PLAN")

        print("-" * 60)



        risk = entry.risk_decision



        if risk:


            if risk.entry_low:


                print(

                    f"Entry Zone : "

                    f"{risk.entry_low:.2f} - "

                    f"{risk.entry_high:.2f}"

                )


            if risk.stop_loss:


                print(

                    f"Stop Loss  : "

                    f"{risk.stop_loss:.2f}"

                )


            if risk.target:


                print(

                    f"Target     : "

                    f"{risk.target:.2f}"

                )


            print(

                f"Risk Reward: "

                f"{risk.risk_reward:.2f}"

            )


            print(

                f"Risk Amount: ₹"

                f"{risk.risk_amount:.2f}"

            )


        else:


            print(

                "Risk plan unavailable"

            )



        print("=" * 60)


        print(
            "BMIE analysis completed."
        )