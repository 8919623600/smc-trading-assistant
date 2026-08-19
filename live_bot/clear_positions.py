import os
from alpaca.trading.client import TradingClient

# Load Alpaca keys from your environment variables
API_KEY = os.getenv("APCA_API_KEY_ID") or os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("APCA_API_SECRET_KEY") or os.getenv("ALPACA_SECRET_KEY")

if not API_KEY or not SECRET_KEY:
    raise ValueError("❌ Alpaca API keys are missing from your environment variables. Make sure they are exported in your terminal session.")

# Initialize Alpaca Client (paper=True for paper trading)
client = TradingClient(API_KEY, SECRET_KEY, paper=True)

print("🛑 Cancelling all open orders...")
client.cancel_orders()

print("📉 Closing all open positions...")
client.close_all_positions(cancel_orders=True)

print("✅ Account cleared successfully!")