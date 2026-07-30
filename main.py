"""
main.py

Entry point for the Balaji Market Intelligence Engine (BMIE).

Responsibilities
----------------
- Create trading session
- Execute Market Engine
- Display market report

Author: BMIE Project
"""

from core.session import create_session
from engine.market_engine import MarketEngine


def main():
    """
    BMIE application entry point.
    """

    # ======================================================
    # Banner
    # ======================================================

    print("=" * 60)
    print("BALAJI MARKET INTELLIGENCE ENGINE")
    print("=" * 60)

    # ======================================================
    # Create Trading Session
    # ======================================================

    session = create_session()

    # ======================================================
    # Create Market Engine
    # ======================================================

    engine = MarketEngine(session)

    # ======================================================
    # Run Analysis
    # ======================================================

    engine.run()

    # ======================================================
    # Display Report
    # ======================================================

    engine.print_report()


if __name__ == "__main__":
    main()