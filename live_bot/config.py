import os

# ==========================================
# LIVE TRADING BOT CONFIGURATION (MULTI-ASSET)
# ==========================================

SYMBOLS = ['GLD', 'FXE']
RISK_AMOUNT_USD = 20.0
MIN_RR = 1.5
MAX_RR = 5.0
POLL_INTERVAL_SECONDS = 60

# Securely load API keys from environment variables
TWELVE_DATA_API_KEYS = [
    os.getenv("TWELVE_DATA_API_KEY_1"),
    os.getenv("TWELVE_DATA_API_KEY_2")
]
TWELVE_DATA_API_KEYS = [k for k in TWELVE_DATA_API_KEYS if k]

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")