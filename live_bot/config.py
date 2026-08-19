import os

# ==========================================
# LIVE TRADING BOT CONFIGURATION (ALPACA)
# ==========================================

# Tracked Symbols (Alpaca works best with US stocks/ETFs like GLD, SPY, QQQ)
SYMBOLS = ["GLD"] 

POLL_INTERVAL_SECONDS = 60
RISK_AMOUNT_USD = 20.0
MIN_RR = 1.5
MAX_RR = 5.0

# --- ALPACA API CREDENTIALS ---
APCA_API_KEY_ID = os.getenv("APCA_API_KEY_ID")
APCA_API_SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")
APCA_API_BASE_URL = "https://paper-api.alpaca.markets" # Paper trading endpoint

# --- TELEGRAM NOTIFICATIONS ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")