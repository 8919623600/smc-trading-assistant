import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def save_data(df, filename):
    df = df.reset_index()
    # Rename potential index names (Date, Datetime) to 'datetime'
    df.columns = [c.lower() for c in df.columns]
    if 'date' in df.columns:
        df.rename(columns={'date': 'datetime'}, inplace=True)
    elif 'datetime' not in df.columns:
        df.rename(columns={df.columns[0]: 'datetime'}, inplace=True)
    
    df.to_parquet(filename)
    print(f"✅ Saved {filename} with columns: {list(df.columns)}")

def download_historical_data():
    print("==================================================")
    print("📥 DOWNLOADING DATA & STANDARDIZING COLUMNS")
    print("==================================================")
    ticker = "GC=F"
    end_date = datetime.today()

    # 1M Data (Last 7 days)
    df_1m = yf.download(ticker, start=(end_date - timedelta(days=7)), end=end_date, interval="1m")
    save_data(df_1m, "XAU_USD_1min.parquet")

    # 15M Data (Last 50 days)
    df_15m = yf.download(ticker, start=(end_date - timedelta(days=50)), end=end_date, interval="15m")
    save_data(df_15m, "XAU_USD_15min.parquet")

    # 1H Data (Last 59 days)
    df_1h = yf.download(ticker, start=(end_date - timedelta(days=59)), end=end_date, interval="1h")
    save_data(df_1h, "XAU_USD_1h.parquet")

    # 4H Data (Last 1 year)
    df_4h = yf.download(ticker, start=(end_date - timedelta(days=365)), end=end_date, interval="1d")
    save_data(df_4h, "XAU_USD_4h.parquet")

if __name__ == "__main__":
    download_historical_data()