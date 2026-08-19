import os
import json
from alpaca.trading.client import TradingClient

def clear_all():
    print("==========================================")
    print("🧹 CLEARING ALPACA POSITIONS & LOCAL STATE")
    print("==========================================")

    # 1. Initialize Alpaca client
    api_key = os.getenv("APCA_API_KEY_ID")
    secret_key = os.getenv("APCA_API_SECRET_KEY")

    if not api_key or not secret_key:
        print("❌ Error: Alpaca API credentials not found in environment variables.")
        return

    try:
        client = TradingClient(api_key, secret_key, paper=True)
    except Exception as e:
        print(f"❌ Failed to initialize Alpaca Trading Client: {e}")
        return

    # 2. Cancel all open orders on Alpaca
    print("🛑 Cancelling all open Alpaca orders...")
    try:
        cancel_requests = client.cancel_orders()
        print(f"   • Successfully processed order cancellations.")
    except Exception as e:
        print(f"   • Note on orders cancellation: {e}")

    # 3. Close all open positions on Alpaca
    print("📉 Closing all open Alpaca positions...")
    try:
        client.close_all_positions(cancel_orders=True)
        print(f"   • Successfully closed all open positions.")
    except Exception as e:
        print(f"   • Note on position closure: {e}")

    # 4. Wipe local active trades tracking file
    active_trades_file = "active_trades.json"
    if os.path.exists(active_trades_file):
        try:
            with open(active_trades_file, mode='w') as f:
                json.dump({}, f, indent=4)
            print(f"   • Cleared local tracking file: {active_trades_file}")
        except Exception as e:
            print(f"   • Error clearing local JSON file: {e}")
    else:
        print(f"   • Local file {active_trades_file} not found (skipped).")

    print("==========================================")
    print("✅ Account and local state cleared successfully!")
    print("==========================================")

if __name__ == "__main__":
    clear_all()