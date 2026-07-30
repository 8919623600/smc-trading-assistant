"""
engine/market_engine.py

Market Engine for the Balaji Market Intelligence Engine (BMIE).

Responsibilities
----------------
- Download market data
- Execute SMC analysis
- Store results
- Print analysis summary

Author: BMIE Project
"""

from analyzer import analyze_market
from models import MarketAnalysis


class MarketEngine:
    """
    Coordinates the complete market analysis workflow.
    """

    def __init__(self, session):
        """
        Initialize the Market Engine.
        """

        self.session = session
        self.market = MarketAnalysis()

    # ======================================================
    # Run Analysis
    # ======================================================

    def run(self):
        """
        Execute analysis on all configured timeframes.
        """

        print("\nRunning Multi-Timeframe Analysis...")
        print("-" * 60)

        for name, timeframe in self.session.timeframes.items():

            print(f"Analyzing {name.upper()} ({timeframe})...")

            result = analyze_market(
                session=self.session,
                timeframe=timeframe,
                bars=self.session.bars,
            )

            setattr(self.market, name, result)

        print("\nAnalysis Completed Successfully.")
        print("=" * 60)

        return self.market

    # ======================================================
    # Report
    # ======================================================

    def print_report(self):
        """
        Display the current market analysis.
        """

        for name, result in self.market.as_dict().items():

            if result is None:
                continue

            print("\n" + "=" * 60)
            print(name.upper())
            print("=" * 60)

            print(f"Timeframe : {result.timeframe}")
            print(f"Structure : {result.structure}")
            print(f"BOS       : {result.bos}")
            print(f"CHoCH     : {result.choch}")

        print("\nBMIE analysis completed.")