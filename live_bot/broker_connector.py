import os
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, StopLossRequest, TakeProfitRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass

class MT5BrokerConnector:
    def __init__(self):
        self.api_key = os.getenv("APCA_API_KEY_ID")
        self.secret_key = os.getenv("APCA_API_SECRET_KEY")
        
        try:
            self.client = TradingClient(self.api_key, self.secret_key, paper=True)
        except Exception as e:
            print(f"⚠️ Failed to initialize Alpaca client: {e}")
            self.client = None

    def connect(self):
        if not self.client:
            return False
        try:
            account = self.client.get_account()
            print(f"   🔹 Alpaca API Connection  : ACTIVE [ ✅ Connected ]")
            print(f"      • Account Status       : {account.status}")
            print(f"      • Paper Buying Power   : ${float(account.buying_power):,.2f}")
            return True
        except Exception as e:
            print(f"   🔹 Alpaca API Connection  : FAILED [ ❌ Error: {e} ]")
            return False

    def disconnect(self):
        print("🔌 Alpaca session disconnected safely.")

    def execute_order(self, symbol, order_type, lot_size, sl, tp):
        if not self.client:
            print("❌ Alpaca client is not initialized.")
            return False, None

        try:
            side = OrderSide.BUY if order_type.upper() == "BUY" else OrderSide.SELL
            formatted_symbol = symbol.replace("/", "") if "/" in symbol else symbol

            # --- AUTO-ADJUST SL FOR ALPACA VALIDATION ---
            try:
                latest_bar = self.client.get_stock_latest_bar({"symbol": formatted_symbol})
                current_price = float(latest_bar[formatted_symbol].close)
            except Exception:
                current_price = sl + 0.50

            if side == OrderSide.BUY:
                adjusted_sl = min(sl, current_price - 0.05)
            else:
                adjusted_sl = max(sl, current_price + 0.05)

            # Updated to 10 whole shares/lots as requested
            fixed_qty = 10.0

            order_data = MarketOrderRequest(
                symbol=formatted_symbol,
                qty=fixed_qty,
                side=side,
                time_in_force=TimeInForce.GTC,
                order_class=OrderClass.BRACKET,
                take_profit=TakeProfitRequest(limit_price=round(tp, 2)),
                stop_loss=StopLossRequest(stop_price=round(adjusted_sl, 2))
            )

            response = self.client.submit_order(order_data=order_data)
            ticket_id = str(response.id)
            
            print(f"✅ Alpaca Bracket Order Placed! Ticket ID: {ticket_id} | Qty: {fixed_qty} | SL: {round(adjusted_sl, 2)}")
            return True, ticket_id

        except Exception as e:
            print(f"❌ Alpaca order execution error: {e}")
            return False, None