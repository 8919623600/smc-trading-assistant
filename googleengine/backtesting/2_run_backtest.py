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
    print("🚀 STARTING 15M STRUCTURE-TRAILING SMC BACKTEST")
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

        # Slice 15M data up to current time for structure trailing
        df_15m_current = df_15m_full[df_15m_full["datetime"] <= current_time]

        # --- MANAGE OPEN TRADES WITH 15M STRUCTURE TRAILING ---
        if active_trade is not None:
            c_high = current_bar['high']
            c_low = current_bar['low']
            
            # Time-based exit (8 PM UTC)
            if current_time.hour >= 20:
                pnl_check = (current_bar['close'] - active_trade['entry']) if active_trade['type'] == 'BUY' else (active_trade['entry'] - current_bar['close'])
                if pnl_check > 0:
                    account_balance += pnl_check * (50.0 / abs(active_trade['entry'] - active_trade['initial_sl']))
                    winning_trades += 1
                else:
                    account_balance -= 50.0
                    losing_trades += 1
                active_trade = None
                continue

            hit_tp = False
            hit_sl = False
            
            # Dynamic Structure Trailing SL based on recent 15M Lows/Highs
            if len(df_15m_current) >= 10:
                if active_trade['type'] == 'BUY':
                    # Find recent 15M swing low to trail stop loss behind
                    recent_15m_low = df_15m_current['low'].iloc[-5:].min()
                    if recent_15m_low > active_trade['sl'] and recent_15m_low < current_bar['close']:
                        active_trade['sl'] = recent_15m_low  # Ratchet SL up
                elif active_trade['type'] == 'SELL':
                    # Find recent 15M swing high to trail stop loss behind
                    recent_15m_high = df_15m_current['high'].iloc[-5:].max()
                    if recent_15m_high < active_trade['sl'] and recent_15m_high > current_bar['close']:
                        active_trade['sl'] = recent_15m_high  # Ratchet SL down

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
                    
            if hit_sl:
                # Calculate final PnL based on where SL was finally hit (could be profitable if trailed past entry)
                pnl_pips = (active_trade['sl'] - active_trade['entry']) if active_trade['type'] == 'BUY' else (active_trade['entry'] - active_trade['sl'])
                initial_risk = abs(active_trade['entry'] - active_trade['initial_sl'])
                
                trade_pnl = (pnl_pips / initial_risk) * 50.0
                account_balance += trade_pnl
                
                if trade_pnl > 0:
                    winning_trades += 1
                else:
                    losing_trades += 1
                active_trade = None
                
            elif hit_tp:
                initial_risk = abs(active_trade['entry'] - active_trade['initial_sl'])
                reward_pips = abs(active_trade['tp'] - active_trade['entry'])
                account_balance += (50.0 * (reward_pips / initial_risk))
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
            "15M": df_15m_current.tail(50),
            "1M": df_1m_slice
        }

        signal = engine.analyze(data_dict)
        decision = signal.get("decision")
        params = signal.get("trade_params", {})

        if decision in ["BUY", "SELL"] and params:
            entry = params.get("entry")
            sl = params.get("sl")
            tp = params.get("tp")
            
            if entry and sl:
                active_trade = {
                    "type": decision,
                    "entry": entry,
                    "initial_sl": sl,
                    "sl": sl,
                    "tp": tp
                }
                trades_today += 1
                total_trades += 1

    net_profit = account_balance - starting_balance
    roi = (net_profit / starting_balance) * 100
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

    print("\n" + "="*50)
    print("💰 STRUCTURE TRAILING PERFORMANCE REPORT")
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