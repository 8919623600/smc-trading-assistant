import os
import MetaTrader5 as mt5

class MT5BrokerConnector:
    def __init__(self):
        # Retrieve credentials from environment variables
        self.login = os.getenv("MT5_LOGIN")
        self.password = os.getenv("MT5_PASSWORD")
        self.server = os.getenv("MT5_SERVER")
        
        # Convert login to integer if present
        if self.login:
            try:
                self.login = int(self.login)
            except ValueError:
                pass
                
        self.client_initialized = self.connect()

    def connect(self):
        if not self.login or not self.password or not self.server:
            print("❌ MT5 credentials missing from environment variables (MT5_LOGIN, MT5_PASSWORD, MT5_SERVER).")
            return False

        # Initialize MT5 connection
        if not mt5.initialize():
            print(f"⚠️ Failed to initialize MT5, error code = {mt5.last_error()}")
            mt5.shutdown()
            return False
        
        # Log into the demo account
        authorized = mt5.login(self.login, password=self.password, server=self.server)
        if not authorized:
            print(f"❌ Failed to connect to MT5 account {self.login}, error code = {mt5.last_error()}")
            mt5.shutdown()
            return False
            
        print(f"   🔹 MT5 API Connection     : ACTIVE [ ✅ Connected ]")
        print(f"      • Account Login        : {self.login}")
        print(f"      • Server               : {self.server}")
        return True

    def disconnect(self):
        mt5.shutdown()
        print("🔌 MT5 session disconnected safely.")

    def execute_order(self, symbol, order_type, lot_size=0.1, sl=None, tp=None):
        if not self.client_initialized:
            print("❌ MT5 client is not connected.")
            return False, None

        # Clean symbol formatting for Forex (e.g., EUR/USD -> EURUSD)
        formatted_symbol = symbol.replace("/", "").upper()
        
        symbol_info = mt5.symbol_info(formatted_symbol)
        if symbol_info is None:
            print(f"❌ Symbol {formatted_symbol} not found in MT5 Market Watch.")
            return False, None

        if not symbol_info.visible:
            if not mt5.symbol_select(formatted_symbol, True):
                print(f"❌ Failed to select symbol {formatted_symbol} in Market Watch.")
                return False, None

        # Determine price and order action type
        if order_type.upper() == 'BUY':
            price = mt5.symbol_info_tick(formatted_symbol).ask
            action_type = mt5.ORDER_TYPE_BUY
        else:
            price = mt5.symbol_info_tick(formatted_symbol).bid
            action_type = mt5.ORDER_TYPE_SELL

        # Enforce 0.1 lot size as requested
        fixed_lot = 0.1

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": formatted_symbol,
            "volume": float(fixed_lot),
            "type": action_type,
            "price": price,
            "deviation": 20,
            "magic": 234000,
            "comment": "SMC Python Bot",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }

        if sl is not None:
            request["sl"] = float(round(sl, 5))
        if tp is not None:
            request["tp"] = float(round(tp, 5))

        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            err_code = result.retcode if result else mt5.last_error()
            print(f"❌ MT5 order execution error: retcode={err_code}")
            return False, None

        ticket_id = str(result.order)
        print(f"✅ MT5 Order Placed! Ticket ID: {ticket_id} | Vol: {fixed_lot} | Price: {price} | SL: {sl} | TP: {tp}")
        return True, ticket_id