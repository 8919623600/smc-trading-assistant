import os
import pandas as pd
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from smc_engine import SMCTradingEngine

def sanitize_df(df):
    """Ensures 'datetime' column exists and is normalized to UTC datetime."""
    # Flatten multiindex columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]
        
    df.columns = [str(c).lower() for c in df.columns]
    
    if 'date' in df.columns and 'datetime' not in df.columns:
        df.rename(columns={'date': 'datetime'}, inplace=True)
    elif 'datetime' not in df.columns:
        df.rename(columns={df.columns[0]: 'datetime'}, inplace=True)
        
    # Convert to datetime and localize/convert to UTC to prevent tz-naive vs tz-aware crashes
    df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')
    if df['datetime'].dt.tz is None:
        df['datetime'] = df['datetime'].dt.tz_localize('UTC')
    else:
        df['datetime'] = df['datetime'].dt.tz_convert('UTC')
        
    df = df.dropna(subset=['datetime']).sort_values('datetime').reset_index(drop=True)
    return df

def run_offline_backtest():
    print("==================================================")
    print("🚀 STARTING FILTERED SMC BACKTEST (Timezone Safe)")
    print("==================================================")
    
    # Load and Sanitize all timeframes
    try:
        df_1m_full = sanitize_df(pd.read_parquet("XAU_USD_1min.parquet"))
        df_15m_full = sanitize_df(pd.read_parquet("XAU_USD_15min.parquet"))
        df_1h_full = sanitize_df(pd.read_parquet("XAU_USD_1h.parquet"))
        df_4h_full = sanitize_df(pd.read_parquet("XAU_USD_4h.parquet"))
        print("✅ Local caches loaded and timezone-synchronized successfully.")
    except Exception as e:
        print(f"❌ Error loading files: {e}")
        return

    print(f"📊 Simulating across {len(df_1m_full)} historical 1M bars...")

    engine = SMCTradingEngine()
    account_balance = 1000.0
    starting_balance = 1000.0
    winning_trades = 0
    losing_trades = 0
    total_trades = 0
    
    current_day = None
    trades_today = 0
    active_trade = None

    for i in range(200, len(df_1m_full)):
        current_bar = df_1m_full.iloc[i]
        current_time = current_bar['datetime']
        
        # Reset daily trade counter on new day
        if current_time.date() != current_day:
            current_day = current_time.date()
            trades_today = 0

        # --- MANAGE OPEN TRADES (Bar-by-Bar SL/TP Check) ---
        if active_trade is not None:
            c_high = current_bar['high']
            c_low = current_bar['low']
            
            hit_tp = False
            hit_sl = False
            
            if active_trade['type'] == 'BUY':
                if c_high >= active_trade['tp']:
                    hit_tp = True
                if c_low <= active_trade['sl']:
                    hit_sl = True
            elif active_trade['type'] == 'SELL':
                if c_low <= active_trade['tp']:
                    hit_tp = True
                if c_high >= active_trade['sl']:
                    hit_sl = True
                    
            # Conservative tie-breaker: if both hit on same candle, count as loss
            if hit_sl and hit_tp:
                account_balance -= 50.0  # Fixed $50 risk
                losing_trades += 1
                active_trade = None
            elif hit_sl:
                account_balance -= 50.0
                losing_trades += 1
                active_trade = None
            elif hit_tp:
                risk_amount = 50.0
                reward_gain = risk_amount * active_trade['rr']
                account_balance += reward_gain
                winning_trades += 1
                active_trade = None
                
            continue  # Skip entry evaluation while in an active trade

        # --- CHECK SESSION & TRADE CAP FILTERS ---
        # Active hours: 7:00 AM to 7:00 PM UTC (London & NY)
        if not (7 <= current_time.hour <= 19):
            continue
            
        if trades_today >= 4:
            continue

        # --- SLICE MULTI-TIMEFRAME DATA ---
        df_1m_slice = df_1m_full.iloc[i-200:i].copy()
        data_dict = {
            "4H": df_4h_full[df_4h_full["datetime"] <= current_time].tail(50),
            "1H": df_1h_full[df_1h_full["datetime"] <= current_time].tail(50),
            "15M": df_15m_full[df_15m_full["datetime"] <= current_time].tail(50),
            "1M": df_1m_slice
        }

        # Run Engine Analysis
        signal = engine.analyze(data_dict)
        decision = signal.get("decision")
        params = signal.get("trade_params", {})

        if decision in ["BUY", "SELL"] and params:
            entry = params.get("entry")
            sl = params.get("sl")
            tp = params.get("tp")
            
            if entry and sl and tp:
                # Calculate RR dynamically
                risk = abs(entry - sl)
                reward = abs(tp - entry)
                rr = reward / risk if risk > 0 else 2.0
                
                active_trade = {
                    "type": decision,
                    "entry": entry,
                    "sl": sl,
                    "tp": tp,
                    "rr": rr
                }
                trades_today += 1
                total_trades += 1

    # --- PERFORMANCE REPORT ---
    net_profit = account_balance - starting_balance
    roi = (net_profit / starting_balance) * 100
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

    print("\n" + "="*50)
    print("💰 FILTERED ACCOUNT PERFORMANCE REPORT")
    print("="*50)
    print(f"Starting Balance:  ${starting_balance:,.2f}")
    print(f"Ending Balance:    ${account_balance:,.2f}")
    print(f"Net Profit/Loss:   ${net_profit:+,.2f}")
    print(f"Return on Invest:  {roi:+.2f}%")
    print(f"Total Trades:      {total_trades}")
    print(f"Winning Trades:    {winning_trades}")
    print(f"Losing Trades:     {losing_trades}")
    print(f"Win Rate:          {win_rate:.2f}%")
    print("="*50)

if __name__ == "__main__":
    run_offline_backtest()