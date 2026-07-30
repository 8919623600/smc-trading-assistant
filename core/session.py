"""
core/session.py

Creates and manages the active trading session.

The TradingSession object stores all information
required during a BMIE execution.

Author: BMIE Project
"""

from dataclasses import dataclass, field

from config import (
    TIMEFRAMES,
    DEFAULT_BARS,
    RISK_PER_TRADE,
    MAX_DAILY_LOSS_PERCENT,
    TARGET_DAILY_PROFIT_PERCENT,
    MINIMUM_RISK_REWARD,
    MINIMUM_CONFIDENCE,
)


@dataclass
class TradingSession:
    """
    Stores the complete trading session.
    """

    symbol: str
    exchange: str
    balance: float

    bars: int = DEFAULT_BARS

    timeframes: dict = field(
        default_factory=lambda: TIMEFRAMES.copy()
    )

    risk_per_trade: float = RISK_PER_TRADE
    max_daily_loss: float = MAX_DAILY_LOSS_PERCENT
    daily_profit_target: float = TARGET_DAILY_PROFIT_PERCENT
    minimum_rr: float = MINIMUM_RISK_REWARD
    minimum_confidence: int = MINIMUM_CONFIDENCE


def create_session() -> TradingSession:
    """
    Ask the user for session information and
    return a TradingSession object.
    """

    print("\n" + "=" * 60)
    print("BALAJI MARKET INTELLIGENCE ENGINE")
    print("=" * 60)

    symbol = input("Enter Symbol   : ").strip().upper()
    exchange = input("Enter Exchange : ").strip().upper()

    balance = float(input("Account Balance : ₹"))

    print("\nSession Created Successfully.\n")

    return TradingSession(
        symbol=symbol,
        exchange=exchange,
        balance=balance,
    )