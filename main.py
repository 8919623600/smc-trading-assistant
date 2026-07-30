"""
main.py

Entry point for the Balaji Market Intelligence Engine (BMIE).

Responsibilities:
- Create trading session
- Run multi-timeframe analysis
- Display summary

Author: BMIE Project
"""

from core.session import create_session
from analyzer import analyze_market


def main():

    # ============================================
    # Create Trading Session
    # ============================================

    session = create_session()

    print("\nRunning Multi-Timeframe Analysis...")
    print("-" * 60)

    analyses = {}

    # Analyze every configured timeframe
    for name, timeframe in session.timeframes.items():

        print(f"Analyzing {name.upper()} ({timeframe})...")

        analyses[name] = analyze_market(
            session=session,
            timeframe=timeframe,
            bars=session.bars,
        )

    print("\nAnalysis Completed Successfully.")
    print("=" * 60)

    # Temporary Summary
    for name, result in analyses.items():

        print(f"\n{name.upper()}")

        print(f"Timeframe : {result.timeframe}")
        print(f"Structure : {result.structure}")
        print(f"BOS       : {result.bos}")

    print("\nBMIE analysis completed.")


if __name__ == "__main__":
    main()