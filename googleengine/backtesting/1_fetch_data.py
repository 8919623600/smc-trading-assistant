import yfinance as yf
import pandas as pd

def download_data():
    print("Downloading historical data...")
    
    # Example: Fetching max available intraday/hourly data for Gold (GC=F or XAUUSD=X)
    # Adjust ticker and intervals as needed
    ticker = "GC=F" 
    
    df_1h = yf.download(ticker, period="60d", interval="1h")
    df_15m = yf.download(ticker, period="59d", interval="15m")
    df_1m = yf.download(ticker, period="7d", interval="1m") # 1m restricted to last 7-30 days on free feeds
    
    # Save to parquet files matching your engine expectations
    for df, filename in [(df_1m, "XAU_USD_1min.parquet"), 
                         (df_15m, "XAU_USD_15min.parquet"), 
                         (df_1h, "XAU_USD_1h.parquet")]:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
        df.reset_index(inplace=True)
        # Standardize datetime column name
        if 'Datetime' in df.columns:
            df.rename(columns={'Datetime': 'datetime'}, inplace=True)
        elif 'Date' in df.columns:
            df.rename(columns={'Date': 'datetime'}, inplace=True)
            
        df.to_parquet(filename)
        print(f"Saved {filename} with {len(df)} rows.")

if __name__ == "__main__":
    download_data()