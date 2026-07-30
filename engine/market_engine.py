"""
engine/market_engine.py

BMIE Market Engine

Responsibilities
----------------
- Run multi-timeframe market analysis
- Store analysis results
- Print formatted market report
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

            print(f"Analyzing {name.upper()} ({timeframe})...")

            result = analyze_market(
                self.session,
                timeframe,
            )

            setattr(self.analysis, name, result)

        print("\nAnalysis Completed Successfully.")

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
    # Print Report
    # ======================================================

    def print_report(self):

        print("=" * 60)

        for section, result in self.analysis.as_dict().items():

            if result is None:
                continue

            print(f"\n{section.upper()}")
            print("=" * 60)

            print(f"Timeframe      : {result.timeframe}")
            print(f"Current Price  : {result.current_price:.2f}")
            print(f"Current Time   : {result.current_time}")

            print()

            print(f"Structure      : {result.structure}")

            if result.market_structure:

                print(f"Trend          : {result.market_structure.trend}")
                print(f"State          : {result.market_structure.state}")

            print()

            print(f"BOS            : {self.format_event(result.bos)}")
            print(f"CHoCH          : {self.format_event(result.choch)}")

            print()

            print(f"Confidence     : {result.confidence:.2f}%")

        print("\nBMIE analysis completed.")