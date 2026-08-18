import os
import pandas as pd
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from smc_engine import SMCTradingEngine

def sanitize_df(df):
    """Ensures 'datetime' column exists."""
    df.columns = [c.lower() for c in df.columns]
    if 'date' in df.columns and 'datetime' not in df.columns:
        df.rename(columns={'date': 'datetime'}, inplace=True)
    return df

def run_offline_backtest():
    print("🚀 STARTING FILTERED SMC BACKTEST")
    
    # Load and Sanitize
    try:
        df_1m_full = sanitize_df(pd.read_parquet("XAU_USD_1min.parquet"))
        df_15m_full = sanitize_df(pd.read_parquet("XAU_USD_15min.parquet"))
        df_1h_full = sanitize_df(pd.read_parquet("XAU_USD_1h.parquet"))
        df_4h_full = sanitize_df(pd.read_parquet("XAU_USD_4h.parquet"))
    except Exception as e:
        print(f"❌ Error loading files: {e}")
        return

    # Backtest Loop
    engine = SMCTradingEngine()
    account_balance = 1000.0
    trades_executed = []
    current_day = None
    trades_today = 0
    
    # Ensure datetime is datetime object for comparisons
    df_1m_full['datetime'] = pd.to_datetime(df_1m_full['datetime'], utc=True)
    
    for i in range(200, len(df_1m_full)):
        current_bar = df_1m_full.iloc[i]
        current_time = current_bar['datetime']
        
        # Reset daily counter
        if current_time.date() != current_day:
            current_day = current_time.date()
            trades_today = 0
            
        # Analysis
        df_1m_slice = df_1m_full.iloc[i-200:i]
        data_dict = {
            "4H": df_4h_full[df_4h_full["datetime"] <= current_time].tail(50),
            "1H": df_1h_full[df_1h_full["datetime"] <= current_time].tail(50),
            "15M": df_15m_full[df_15m_full["datetime"] <= current_time].tail(50),
            "1M": df_1m_slice
        }
        
        # ... (Rest of your execution logic from previous step)
        # Note: Ensure your engine logic matches the previous snippet provided.
    
    print("✅ Backtest complete.")

if __name__ == "__main__":
    run_offline_backtest()