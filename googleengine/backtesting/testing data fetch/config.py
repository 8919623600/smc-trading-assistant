import os

SYMBOLS = ["EUR/USD", "XAU/USD"]
POLL_INTERVAL_SECONDS = 60

# Dual API keys for rate limit load balancing
TWELVE_DATA_KEYS = [
    os.getenv("TWELVE_DATA_API_KEY_1"),
    os.getenv("TWELVE_DATA_API_KEY_2")
]

# Telegram Credentials
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")