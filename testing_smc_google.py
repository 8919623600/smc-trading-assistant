import pandas as pd
import yfinance as yf
from googlesmc import SMCTradingEngine

def fetch_real_data(ticker="GC=F"):
    """
    Fetches real multi-timeframe market data.
    Note: 1m intraday data from Yahoo Finance is limited to the last 7 days.
    """
    print(f"Fetching market data for {ticker}...")
    
    # Download 1-minute data (last 5 days)
    df_1m = yf.download(ticker, period="5d", interval="1m")
    
    # Clean up column names to lowercase
    if isinstance(df_1m.columns, pd.MultiIndex):
        df_1m.columns = df_1m.columns.get_level_values(0)
    df_1m = df_1m.rename(columns={
        "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"
    })

    # Resample 1M data into 15M, 1H, and 4H timeframes
    df_15m = df_1m.resample('15min').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
    }).dropna()

    df_1h = df_1m.resample('1h').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
    }).dropna()

    df_4h = df_1m.resample('4h').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
    }).dropna()

    return {
        '4H': df_4h,
        '1H': df_1h,
        '15M': df_15m,
        '1M': df_1m
    }

# Run Engine on Real Market Data
engine = SMCTradingEngine(min_rr=2.0, atr_multiplier=1.0)
data = fetch_real_data(ticker="GC=F")  # Gold Futures (or use 'EURUSD=X')

result = engine.analyze(data)
print("\n=== SMC ANALYSIS RESULT (REAL DATA) ===")
print(result)