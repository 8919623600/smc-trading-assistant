import os
import pandas as pd
import sys

# Import your SMC Engine from the parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from smc_engine import SMCTradingEngine

def run_offline_backtest():
    print("==================================================")
    print("🚀 STARTING $1,000 ACCOUNT BACKTEST WITH RELAXED FILTERS")
    print("==================================================")

    starting_balance = 1000.0
    account_balance = starting_balance
    risk_per_trade_usd = 50.0

    # Load cached parquet files
    try:
        df_1m_full = pd.read_parquet("XAU_USD_1min.parquet")
        df_15m_full = pd.read_parquet("XAU_USD_15min.parquet")
        df_1h_full = pd.read_parquet("XAU_USD_1h.parquet")
        df_4h_full = pd.read_parquet("XAU_USD_4h.parquet")
        print("✅ Local cache loaded successfully.")
    except FileNotFoundError as e:
        print(f"❌ Error: Missing cached files. Run `1_download_data.py` first! {e}")
        return

    # --- RELAXED ENGINE PARAMETERS FOR BACKTESTING ---
    engine = SMCTradingEngine(
        min_rr=1.5, max_rr=10.0, atr_multiplier=0.4, backtest_mode=True
    )

    start_index = 200
    total_bars = len(df_1m_full)

    trades_executed = []
    active_trade = None

    print(f"📊 Simulating across {total_bars - start_index} historical 1M bars... (This will run quietly)")

    i = start_index
    while i < total_bars:
        df_1m_slice = df_1m_full.iloc[i - 200 : i]
        current_time = df_1m_slice["datetime"].iloc[-1]
        current_bar = df_1m_full.iloc[i]

        # Keep console quiet, but show progress every 10,000 bars
        if i % 10000 == 0:
            print(f"⏳ Processed {i}/{total_bars} bars...")

        # --- TRACK ACTIVE TRADE BAR-BY-BAR ---
        if active_trade is not None:
            direction = active_trade["direction"]
            entry = active_trade["entry"]
            sl = active_trade["sl"]
            tp = active_trade["tp"]

            high = current_bar["high"]
            low = current_bar["low"]

            hit_sl = False
            hit_tp = False

            if direction == "BUY":
                if low <= sl:
                    hit_sl = True
                if high >= tp:
                    hit_tp = True
            elif direction == "SELL":
                if high >= sl:
                    hit_sl = True
                if low <= tp:
                    hit_tp = True

            if hit_sl and hit_tp:
                outcome = "LOSS"
            elif hit_sl:
                outcome = "LOSS"
            elif hit_tp:
                outcome = "WIN"
            else:
                outcome = None

            if outcome is not None:
                risk_distance = abs(entry - sl)
                reward_distance = abs(tp - entry)
                rr_ratio = (reward_distance / risk_distance if risk_distance > 0 else 1.5)

                trade_pnl = ((risk_per_trade_usd * rr_ratio) if outcome == "WIN" else -risk_per_trade_usd)
                account_balance += trade_pnl

                active_trade["exit_time"] = current_time
                active_trade["outcome"] = outcome
                active_trade["pnl"] = round(trade_pnl, 2)
                trades_executed.append(active_trade)

                if account_balance <= 0:
                    print("⚠️ ACCOUNT BLOWOUT: Balance reached $0.00. Stopping backtest.")
                    break

                active_trade = None

            i += 1
            continue

        # --- SCAN FOR NEW SIGNALS ---
        df_15m_slice = df_15m_full[df_15m_full["datetime"] <= current_time].tail(50)
        df_1h_slice = df_1h_full[df_1h_full["datetime"] <= current_time].tail(50)
        df_4h_slice = df_4h_full[df_4h_full["datetime"] <= current_time].tail(50)

        data_dict = {
            "4H": df_4h_slice,
            "1H": df_1h_slice,
            "15M": df_15m_slice,
            "1M": df_1m_slice,
        }

        analysis_result = engine.analyze(data_dict)
        decision = analysis_result["decision"]

        if decision in ["BUY", "SELL"]:
            trade_params = analysis_result.get("trade_params", {})
            entry = trade_params.get("entry")
            sl = trade_params.get("sl")
            tp = trade_params.get("tp2") or trade_params.get("tp1") or trade_params.get("tp")

            if entry and sl and tp and account_balance > 0:
                active_trade = {
                    "entry_time": current_time,
                    "direction": decision,
                    "entry": entry,
                    "sl": sl,
                    "tp": tp,
                }

        i += 1

    # ==========================================================
    # FINAL FINANCIAL REPORT
    # ==========================================================
    print("\n" + "=" * 50)
    print("💰 FINAL ACCOUNT PERFORMANCE REPORT")
    print("=" * 50)
    print(f"Starting Balance:  ${starting_balance:,.2f}")
    print(f"Ending Balance:    ${account_balance:,.2f}")
    
    net_profit = account_balance - starting_balance
    roi = (net_profit / starting_balance) * 100
    
    print(f"Net Profit/Loss:   ${net_profit:+,.2f}")
    print(f"Return on Invest:  {roi:+.2f}%")
    
    total_trades = len(trades_executed)
    print(f"Total Trades:      {total_trades}")

    if total_trades > 0:
        wins = len([t for t in trades_executed if t.get("outcome") == "WIN"])
        losses = total_trades - wins
        win_rate = (wins / total_trades) * 100
        
        print(f"Winning Trades:    {wins}")
        print(f"Losing Trades:     {losses}")
        print(f"Win Rate:          {win_rate:.2f}%")

    print("=" * 50)

if __name__ == "__main__":
    run_offline_backtest()