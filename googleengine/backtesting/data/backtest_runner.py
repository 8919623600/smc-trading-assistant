import pandas as pd
from smc_engine import AdvancedSMCEngine

def run_historical_backtest(file_paths_dict, symbol="EUR/USD"):
    print(f"=== INITIALIZING BACKTEST FOR {symbol} ===")
    
    # Load multi-timeframe dataframes
    data_dict = {tf: pd.read_csv(path) for tf, path in file_paths_dict.items()}
    engine = AdvancedSMCEngine(min_rr=2.0, max_rr=8.0)
    
    closed_trades = []
    df_1m = data_dict["1M"]
    total_bars = len(df_1m)
    
    # Sliding window simulation over 1M candles
    for i in range(100, total_bars - 50):
        # Safe proportional slicing across timeframes
        h4_idx = min(len(data_dict["4H"]), max(10, i // 60))
        h1_idx = min(len(data_dict["1H"]), max(10, i // 15))
        m15_idx = min(len(data_dict["15M"]), max(10, i // 4))
        
        slice_dict = {
            "4H": data_dict["4H"].iloc[:h4_idx],
            "1H": data_dict["1H"].iloc[:h1_idx],
            "15M": data_dict["15M"].iloc[:m15_idx],
            "1M": df_1m.iloc[:i]
        }
        
        signal = engine.analyze(slice_dict, symbol=symbol)
        
        if signal["decision"] in ["BUY", "SELL"]:
            entry = signal["trade_params"]["entry"]
            sl = signal["trade_params"]["sl"]
            tp2 = signal["trade_params"]["tp2"]
            direction = signal["decision"]
            
            # Forward-check outcome in subsequent bars
            future_candles = df_1m.iloc[i:i+30]
            trade_result = "PENDING"
            pnl_pips = 0
            
            for _, bar in future_candles.iterrows():
                if direction == "BUY":
                    if bar['low'] <= sl:
                        trade_result = "LOSS"
                        pnl_pips = sl - entry
                        break
                    elif bar['high'] >= tp2:
                        trade_result = "WIN"
                        pnl_pips = tp2 - entry
                        break
                elif direction == "SELL":
                    if bar['high'] >= sl:
                        trade_result = "LOSS"
                        pnl_pips = entry - sl
                        break
                    elif bar['low'] <= tp2:
                        trade_result = "WIN"
                        pnl_pips = entry - tp2
                        break
            
            if trade_result != "PENDING":
                closed_trades.append({
                    "result": trade_result, 
                    "pnl": pnl_pips, 
                    "rr": signal["trade_params"]["rr"]
                })
                
    # Performance Review Summary
    total_closed = len(closed_trades)
    if total_closed == 0:
        print("[PERFORMANCE REVIEW] No trades triggered during backtest window.")
        return
        
    wins = sum(1 for t in closed_trades if t["result"] == "WIN")
    losses = sum(1 for t in closed_trades if t["result"] == "LOSS")
    win_rate = (wins / total_closed) * 100
    net_score = sum(t["pnl"] for t in closed_trades)
    
    print("==================================================")
    print("           BACKTEST PERFORMANCE REVIEW            ")
    print("==================================================")
    print(f"• Total Trades Closed: {total_closed}")
    print(f"• Winning Trades:      {wins} 🟢")
    print(f"• Losing Trades:       {losses} ❌")
    print(f"• Win Rate:            {win_rate:.1f}%")
    print(f"• Net Score PnL:       {net_score:.4f}")
    print("==================================================")

if __name__ == "__main__":
    file_paths = {
        "4H": "data/eurusd_4h.csv",
        "1H": "data/eurusd_1h.csv",
        "15M": "data/eurusd_15m.csv",
        "1M": "data/eurusd_1m.csv"
    }
    run_historical_backtest(file_paths, symbol="EUR/USD")