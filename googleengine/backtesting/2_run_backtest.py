import os
import pandas as pd
import numpy as np
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from smc_engine import SMCTradingEngine

def sanitize_df(df):
    """Ensures 'datetime' column exists and is normalized to UTC datetime."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]
        
    df.columns = [str(c).lower() for c in df.columns]
    
    if 'date' in df.columns and 'datetime' not in df.columns:
        df.rename(columns={'date': 'datetime'}, inplace=True)
    elif 'datetime' not in df.columns:
        df.rename(columns={df.columns[0]: 'datetime'}, inplace=True)
        
    df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')
    if df['datetime'].dt.tz is None:
        df['datetime'] = df['datetime'].dt.tz_localize('UTC')
    else:
        df['datetime'] = df['datetime'].dt.tz_convert('UTC')
        
    df = df.dropna(subset=['datetime']).sort_values('datetime').reset_index(drop=True)
    return df

def run_offline_backtest():
    print("==================================================")
    print("🚀 STARTING OPTIMIZED SMC BACKTEST (3.5 RR & 1.5R BE)")
    print("==================================================")
    
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
        
        if current_time.date() != current_day:
            current_day = current_time.date()
            trades_today = 0

        # --- MANAGE OPEN TRADES ---
        if active_trade is not None:
            c_high = current_bar['high']
            c_low = current_bar['low']
            
            # Time-based exit (8 PM UTC)
            if current_time.hour >= 20:
                pnl_check = (current_bar['close'] - active_trade['entry']) if active_trade['type'] == 'BUY' else (active_trade['entry'] - current_bar['close'])
                if pnl_check > 0:
                    account_balance += pnl_check * (50.0 / abs(active_trade['entry'] - active_trade['sl']))
                    winning_trades += 1
                else:
                    account_balance -= 50.0
                    losing_trades += 1
                active_trade = None
                continue

            hit_tp = False
            hit_sl = False
            
            risk_dist = abs(active_trade['entry'] - active_trade['sl'])
            
            if active_trade['type'] == 'BUY':
                # Delayed Breakeven: move SL to entry only after reaching 1.5R profit
                if c_high >= (active_trade['entry'] + (risk_dist * 1.5)) and active_trade['sl'] < active_trade['entry']:
                    active_trade['sl'] = active_trade['entry']
                
                if c_high >= active_trade['tp']:
                    hit_tp = True
                if c_low <= active_trade['sl']:
                    hit_sl = True
                    
            elif active_trade['type'] == 'SELL':
                if c_low <= (active_trade['entry'] - (risk_dist * 1.5)) and active_trade['sl'] > active_trade['entry']:
                    active_trade['sl'] = active_trade['entry']
                
                if c_low <= active_trade['tp']:
                    hit_tp = True
                if c_high >= active_trade['sl']:
                    hit_sl = True
                    
            if hit_sl and hit_tp:
                account_balance -= 50.0  
                losing_trades += 1
                active_trade = None
            elif hit_sl:
                loss_cost = 0.0 if active_trade['sl'] == active_trade['entry'] else 50.0
                account_balance -= loss_cost
                if loss_cost > 0:
                    losing_trades += 1
                else:
                    total_trades -= 1
                active_trade = None
            elif hit_tp:
                account_balance += (50.0 * active_trade['rr'])
                winning_trades += 1
                active_trade = None
                
            continue

        # Filters: Session hours & daily cap
        if not (8 <= current_time.hour <= 17):
            continue
            
        if trades_today >= 2:
            continue

        df_1m_slice = df_1m_full.iloc[i-200:i].copy()
        
        # Volatility check
        df_1m_slice['tr'] = np.maximum(df_1m_slice['high'] - df_1m_slice['low'], 
                                       np.maximum(abs(df_1m_slice['high'] - df_1m_slice['close'].shift(1)), 
                                                  abs(df_1m_slice['low'] - df_1m_slice['close'].shift(1))))
        rolling_atr = df_1m_slice['tr'].rolling(14).mean().iloc[-1]
        mean_atr = df_1m_slice['tr'].rolling(50).mean().iloc[-1]
        if not pd.isna(rolling_atr) and not pd.isna(mean_atr) and rolling_atr > (mean_atr * 2.0):
            continue

        data_dict = {
            "4H": df_4h_full[df_4h_full["datetime"] <= current_time].tail(50),
            "1H": df_1h_full[df_1h_full["datetime"] <= current_time].tail(50),
            "15M": df_15m_full[df_15m_full["datetime"] <= current_time].tail(50),
            "1M": df_1m_slice
        }

        signal = engine.analyze(data_dict)
        decision = signal.get("decision")
        params = signal.get("trade_params", {})

        if decision in ["BUY", "SELL"] and params:
            entry = params.get("entry")
            sl = params.get("sl")
            
            if entry and sl:
                # Force target to 3.5 Risk-to-Reward ratio
                risk = abs(entry - sl)
                if decision == "BUY":
                    tp = entry + (risk * 3.5)
                else:
                    tp = entry - (risk * 3.5)
                
                active_trade = {
                    "type": decision,
                    "entry": entry,
                    "sl": sl,
                    "tp": tp,
                    "rr": 3.5
                }
                trades_today += 1
                total_trades += 1

    net_profit = account_balance - starting_balance
    roi = (net_profit / starting_balance) * 100
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

    print("\n" + "="*50)
    print("💰 OPTIMIZED PERFORMANCE REPORT")
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