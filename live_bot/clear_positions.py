import os
import json
from alpaca.trading.client import TradingClient

# Initialize Alpaca client
api_key = os.getenv("APCA_API_KEY_ID")
secret_key = os.getenv("APCA_API_SECRET_KEY")
client = TradingClient(api_key, secret_key, paper=True)

print("🛑 Cancelling all open Alpaca orders...")
try:
    client.cancel_orders()
except Exception as e:
    print(f"Note on orders: {e}")

print("📉 Closing all open Alpaca positions...")
try:
    client.close_all_positions(cancel_orders=True)
except Exception as e:
    print(f"Note on positions: {e}")

# Clear local tracking file
ACTIVE_TRADES_FILE = "active_trades.json"
if os.path.exists(ACTIVE_TRADES_FILE):
    with open(ACTIVE_TRADES_FILE, mode='w') as f:
        json.dump({}, f)
    print("🧹 Cleared local active_trades.json tracker file.")

print("✅ Account and local state cleared successfully!")