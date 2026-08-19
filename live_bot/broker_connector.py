import MetaTrader5 as mt5

class MT5BrokerConnector:
    def __init__(self):
        self.connected = False

    def connect(self):
        """Safely initialize connection to MT5 terminal."""
        try:
            if not mt5.initialize():
                print(f"⚠️ MT5 initialization failed: {mt5.last_error()}")
                self.connected = False
                return False
            self.connected = True
            return True
        except Exception as e:
            print(f"❌ Exception connecting to MT5: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """Safely close MT5 connection."""
        if self.connected:
            try:
                mt5.shutdown()
            except:
                pass
            self.connected = False

    def execute_order(self, symbol, order_type, lot_size, sl, tp2):
        """
        Executes a paper order safely. Returns (success_bool, ticket_id).
        Will not crash the bot if execution fails.
        """
        if not self.connect():
            print("⚠️ Skipping broker execution: MT5 not connected.")
            return False, None

        try:
            # Format symbol for MT5 (e.g., XAUUSD or EURUSD)
            mt5_symbol = symbol.replace("/", "")
            symbol_info = mt5.symbol_info(mt5_symbol)
            
            if symbol_info is None:
                mt5_symbol = symbol  # Fallback to original
                symbol_info = mt5.symbol_info(mt5_symbol)
                if symbol_info is None:
                    print(f"❌ MT5 Symbol {symbol} not found in Market Watch.")
                    return False, None

            if not symbol_info.visible:
                if not mt5.symbol_select(mt5_symbol, True):
                    print(f"❌ Failed to select symbol {mt5_symbol} in Market Watch.")
                    return False, None

            tick = mt5.symbol_info_tick(mt5_symbol)
            if tick is None:
                print(f"❌ Failed to get tick data for {mt5_symbol}")
                return False, None

            action = mt5.ORDER_TYPE_BUY if order_type == "BUY" else mt5.ORDER_TYPE_SELL
            price = tick.ask if order_type == "BUY" else tick.bid

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": mt5_symbol,
                "volume": float(lot_size),
                "type": action,
                "price": price,
                "sl": float(sl),
                "tp": float(tp2),
                "deviation": 20,
                "magic": 234000,
                "comment": "SMC Isolated Bot",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_RETURN,
            }

            result = mt5.order_send(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                print(f"❌ MT5 Order Send Failed, retcode={result.retcode}")
                return False, None

            print(f"✅ MT5 Paper Order Executed! Ticket ID: {result.order}")
            return True, result.order

        except Exception as e:
            print(f"❌ Error during MT5 order execution: {e}")
            return False, None