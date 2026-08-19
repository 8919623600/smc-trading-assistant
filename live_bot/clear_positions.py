from alpaca.trading.client import TradingClient
from config import API_KEY, SECRET_KEY, BASE_URL

# Initialize Alpaca Client
client = TradingClient(API_KEY, SECRET_KEY, paper=True)

print("🛑 Cancelling all open orders...")
client.cancel_orders()

print("📉 Closing all open positions...")
client.close_all_positions(cancel_orders=True)

print("✅ Account cleared successfully!")