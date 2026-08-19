import os
import MetaTrader5 as mt5
import pandas as pd

class MT5DataFetcher:
    def __init__(self):
        pass

    def get_historical_candles(self, symbol, timeframe_str="M15", count=200):
        # Clean symbol formatting (e.g., EUR/USD -> EURUSD)
        formatted_symbol = symbol.replace("/", "").upper()
        
        # Map timeframe strings to MT5 constants
        tf_mapping = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1,
        }
        
        tf = tf_mapping.get(timeframe_str.upper(), mt5.TIMEFRAME_M15)
        
        rates = mt5.copy_rates_from_pos(formatted_symbol, tf, 0, count)
        if rates is None or len(rates) == 0:
            print(f"⚠️ Failed to fetch rates for {formatted_symbol}, error code = {mt5.last_error()}")
            return pd.DataFrame()

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        # Standardize columns for your SMC engine
        df = df.rename(columns={'time': 'timestamp', 'tick_volume': 'volume'})
        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]