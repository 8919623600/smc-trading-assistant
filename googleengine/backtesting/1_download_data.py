import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def download_historical_data():
    print("==================================================")
    print("📥 DOWNLOADING ROLLING 1M DATA SAFELY (YFINANCE BYPASS)")
    print("==================================================")

    ticker = "GC=F"
    
    # Yahoo allows max 7-8 days for 1m data at a time. Let's pull the last 7 days.
    # (For custom historical months, you must chunk them in 7-day increments).
    end_date = datetime.today()
    start_date = end_date - timedelta(days=7)

    print(f"Fetching 1M data from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}...")

    # 1. Download 1-minute data safely within the 7-day window
    df_1m = yf.download(ticker, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), interval="1m")
    if df_1m.empty:
        print("❌ Error: 1M download returned empty. Check date range or network.")
        return

    df_1m.reset_index(inplace=True)
    df_1m.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df_1m.columns]
    df_1m.to_parquet("XAU_USD_1min.parquet")

    # 2. Download 15-minute data (Safe up to 59 days)
    start_15m = end_date - timedelta(days=50)
    print(f"Fetching 15M data from {start_15m.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}...")
    df_15m = yf.download(ticker, start=start_15m.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), interval="15m")
    df_15m.reset_index(inplace=True)
    df_15m.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df_15m.columns]
    df_15m.to_parquet("XAU_USD_15min.parquet")

    # 3. Download 1-hour data (Safe for longer windows)
    start_1h = end_date - timedelta(days=59)
    df_1h = yf.download(ticker, start=start_1h.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), interval="1h")
    df_1h.reset_index(inplace=True)
    df_1h.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df_1h.columns]
    df_1h.to_parquet("XAU_USD_1h.parquet")

    # 4. Download 4-hour / Daily context data
    df_4h = yf.download(ticker, start="2025-01-01", end=end_date.strftime('%Y-%m-%d'), interval="1d")
    df_4h.reset_index(inplace=True)
    df_4h.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df_4h.columns]
    df_4h.to_parquet("XAU_USD_4h.parquet")

    print("✅ All parquet files downloaded and synced successfully!")

if __name__ == "__main__":
    download_historical_data()