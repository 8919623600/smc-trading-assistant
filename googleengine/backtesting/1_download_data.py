import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

def download_one_month_1m_data():
    print("📥 Downloading 30 days of 1-minute Gold data in 7-day chunks...")
    
    end_date = datetime.utcnow()
    all_data = []
    
    # Loop over the last 4 weeks (28 days)
    for i in range(4):
        chunk_end = end_date - timedelta(days=7 * i)
        chunk_start = chunk_end - timedelta(days=7)
        
        print(f"Fetching chunk: {chunk_start.strftime('%Y-%m-%d')} to {chunk_end.strftime('%Y-%m-%d')}")
        
        # Download 1m data for GC=F (Gold Futures)
        df = yf.download("GC=F", start=chunk_start.strftime('%Y-%m-%d'), end=chunk_end.strftime('%Y-%m-%d'), interval="1m", progress=False)
        
        if not df.empty:
            all_data.append(df)
            
    if len(all_data) > 0:
        full_df = pd.concat(all_data)
        # Clean up multi-index columns if present and format datetime
        full_df = full_df.reset_index()
        
        # Standardize column names
        full_df.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in full_df.columns]
        if 'date' in full_df.columns:
            full_df.rename(columns={'date': 'datetime'}, inplace=True)
        elif 'index' in full_df.columns:
            full_df.rename(columns={'index': 'datetime'}, inplace=True)
            
        full_df.to_parquet("XAU_USD_1min.parquet")
        print("✅ Successfully saved 30 days of 1M data to 'XAU_USD_1min.parquet'!")
    else:
        print("❌ Failed to download data.")

if __name__ == "__main__":
    download_one_month_1m_data()