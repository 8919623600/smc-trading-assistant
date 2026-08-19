import config
from alpaca.trading.client import TradingClient

# Automatically grab whatever key names your config.py is using
api_key = getattr(config, 'API_KEY', None) or getattr(config, 'ALPACA_API_KEY', None) or getattr(config, 'APCA_API_KEY_ID', None)
secret_key = getattr(config, 'SECRET_KEY', None) or getattr(config, 'ALPACA_SECRET_KEY', None) or getattr(config, 'APCA_API_SECRET_KEY', None)

if not api_key or not secret_key:
    raise ValueError("❌ Could not find Alpaca API keys in config.py. Please check your variable names.")

# Initialize Alpaca Client
client = TradingClient(api_key, secret_key, paper=True)

print("🛑 Cancelling all open orders...")
client.cancel_orders()

print("📉 Closing all open positions...")
client.close_all_positions(cancel_orders=True)

print("✅ Account cleared successfully!")