"""
config.py

Central configuration for the
Balaji Market Intelligence Engine (BMIE).

All project-wide configuration values should
be defined here.

Author: BMIE Project
"""

# ==========================================================
# MARKET CONFIGURATION
# ==========================================================

# Trading Symbol
SYMBOL = "XAUUSD"

# Exchange supported by TradingView
EXCHANGE = "OANDA"

# Number of historical candles to download
DEFAULT_BARS = 300

# ==========================================================
# MULTI-TIMEFRAME CONFIGURATION
# ==========================================================

# Default timeframe (used if no timeframe is supplied)
DEFAULT_TIMEFRAME = "15m"

# Timeframes used throughout BMIE
TIMEFRAMES = {
    "bias": "1d",         # Overall Market Bias
    "structure": "4h",    # External Market Structure
    "trend": "1h",        # Trend Confirmation
    "setup": "15m",       # Setup Formation
    "entry": "5m"         # Entry Confirmation
}

# ==========================================================
# SWING DETECTION
# ==========================================================

# Number of candles on each side required
# to confirm a swing high/low
LOOKBACK = 2

# ==========================================================
# MAJOR SWING DETECTION
# ==========================================================

# Minimum strength to classify as a major swing
MAJOR_SWING_STRENGTH = 3

# Maximum lookback used while calculating strength
MAX_STRENGTH_LOOKBACK = 8

# ==========================================================
# RISK MANAGEMENT (Sprint 4)
# ==========================================================

# Percentage risk per trade
RISK_PER_TRADE = 1.0

# Maximum loss allowed in a single trading day
MAX_DAILY_LOSS_PERCENT = 3.0

# Daily profit target
TARGET_DAILY_PROFIT_PERCENT = 6.0

# Minimum acceptable Risk : Reward
MINIMUM_RISK_REWARD = 3.0

# Minimum confidence score required
MINIMUM_CONFIDENCE = 85

# ==========================================================
# ACCOUNT SETTINGS
# ==========================================================

# Manual Mode
#
# True  -> User enters balance manually
# False -> Future Broker Integration
MANUAL_ACCOUNT_MODE = True

# ==========================================================
# CHART SETTINGS
# ==========================================================

CHART_TITLE = "Balaji Market Intelligence Engine"

SAVE_CHARTS = True

# ==========================================================
# DEBUG SETTINGS
# ==========================================================

DEBUG = False