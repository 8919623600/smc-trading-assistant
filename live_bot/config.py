import os

# ==========================================
# LIVE TRADING BOT CONFIGURATION (MT5 / MULTI-ASSET)
# ==========================================

# Multi-asset configuration for Forex and Gold
SYMBOLS = ["EURUSD", "XAUUSD"] 
# Note: If your specific MT5 broker calls Gold "GOLD" instead of "XAUUSD", change it to "GOLD"

POLL_INTERVAL_SECONDS = 60
RISK_AMOUNT_USD = 20.0
MIN_RR = 1.5
MAX_RR = 5.0

# Fixed Lot Size for trades
LOT_SIZE = 0.1

# --- MT5 CREDENTIALS (Loaded from EC2 Environment Variables) ---
MT5_LOGIN = os.getenv("MT5_LOGIN")
MT5_PASSWORD = os.getenv("MT5_PASSWORD")
MT5_SERVER = os.getenv("MT5_SERVER")

# --- TELEGRAM NOTIFICATIONS ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")