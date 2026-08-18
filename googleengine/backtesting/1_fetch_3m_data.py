import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta, timezone

def fetch_3_months_data():
    print("==================================================")
    print("📥 DOWNLOADING 3 MONTHS OF XAU/USD (GC=F) 1M DATA")
    print("==================================================")
    
    ticker = "GC=F" # Gold Futures
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=90)
    
    all_1m = []
    current_start = start_date
    
    # yfinance limits 1m data to 7-day chunks, so we loop through 90 days
    while current_start < end_date:
        current_end = min(current_start + timedelta(days=7), end_date)
        print(f"Fetching chunk: {current_start.date()} to {current_end.date()}...")
        
        df = yf.download(ticker, start=current_start, end=current_end, interval="1m", progress=False)
        if not df.empty:
            all_1m.append(df)
            
        current_start = current_end
        
    if not all_1m:
        print("❌ Failed to download historical data.")
        return
        
    df_1m = pd.concat(all_1m)
    df_1m.reset_index(inplace=True)
    
    # Clean up multi-index columns if yfinance returns them
    if isinstance(df_1m.columns, pd.MultiIndex):
        df_1m.columns = [col[0] for col in df_1m.columns]
        
    df_1m.columns = [str(c).lower() for c in df_1m.columns]
    
    if 'datetime' not in df_1m.columns:
        if 'date' in df_1m.columns:
            df_1m.rename(columns={'date': 'datetime'}, inplace=True)
        elif 'index' in df_1m.columns:
            df_1m.rename(columns={'index': 'datetime'}, inplace=True)
            
    df_1m['datetime'] = pd.to_datetime(df_1m['datetime'], errors='coerce')
    df_1m = df_1m.dropna(subset=['datetime']).sort_values('datetime').drop_duplicates(subset=['datetime']).reset_index(drop=True)
    
    # Save 1m Parquet
    df_1m.to_parquet("XAU_USD_1min.parquet")
    print(f"✅ Saved XAU_USD_1min.parquet with {len(df_1m):,} bars.")
    
    # Resample for higher timeframes
    df_1m.set_index('datetime', inplace=True)
    
    df_15m = df_1m.resample('15min').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna().reset_index()
    df_1h = df_1m.resample('1h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna().reset_index()
    df_4h = df_1m.resample('4h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna().reset_index()
    
    df_15m.to_parquet("XAU_USD_15min.parquet")
    df_1h.to_parquet("XAU_USD_1h.parquet")
    df_4h.to_parquet("XAU_USD_4h.parquet")
    
    print("✅ Successfully resampled and saved 15M, 1H, and 4H parquet files!")
    print("==================================================")

if __name__ == "__main__":
    fetch_3_months_data()