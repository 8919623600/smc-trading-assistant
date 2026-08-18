import yfinance as yf
import pandas as pd

def download_historical_data():
    print("==================================================")
    print("📥 DOWNLOADING CUSTOM HISTORICAL DATA FOR BACKTEST")
    print("==================================================")

    # Define your target symbol (Gold)
    ticker = "GC=F" # Yahoo Finance ticker for Gold futures

    # --- SET YOUR CUSTOM DATE RANGE HERE ---
    # Note: Yahoo Finance provides 1-minute data for rolling 60-day windows.
    # For higher timeframes (15m, 1h, 4h, 1d), you can go back years.
    start_date = "2026-01-01"
    end_date = "2026-02-01"

    print(f"Fetching data from {start_date} to {end_date}...")

    # 1. Download 1-minute data (Safe within the recent 60-day window)
    df_1m = yf.download(ticker, start=start_date, end=end_date, interval="1m")
    df_1m.reset_index(inplace=True)
    df_1m.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df_1m.columns]
    df_1m.to_parquet("XAU_USD_1min.parquet")

    # 2. Download 15-minute data
    df_15m = yf.download(ticker, start=start_date, end=end_date, interval="15m")
    df_15m.reset_index(inplace=True)
    df_15m.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df_15m.columns]
    df_15m.to_parquet("XAU_USD_15min.parquet")

    # 3. Download 1-hour data
    df_1h = yf.download(ticker, start=start_date, end=end_date, interval="1h")
    df_1h.reset_index(inplace=True)
    df_1h.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df_1h.columns]
    df_1h.to_parquet("XAU_USD_1h.parquet")

    # 4. Download 4-hour / Daily context data
    df_4h = yf.download(ticker, start=start_date, end=end_date, interval="1d")
    df_4h.reset_index(inplace=True)
    df_4h.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df_4h.columns]
    df_4h.to_parquet("XAU_USD_4h.parquet")

    print("✅ All custom parquet files saved successfully!")

if __name__ == "__main__":
    download_historical_data()