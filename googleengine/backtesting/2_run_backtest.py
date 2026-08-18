import os
import pandas as pd

# Import your SMC Engine from the parent directory
import sys

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
  # Lowered min_rr to 1.5 and adjusted multiplier to catch more setups
  engine = SMCTradingEngine(
    min_rr=1.5, max_rr=10.0, atr_multiplier=0.4, backtest_mode=True
)

  # Optional flags if supported by your engine class to bypass strict filters:
  # engine.require_strict_ote = False
  # engine.bypass_1h_sweep = True

  start_index = 200
  total_bars = len(df_1m_full)

  trades_executed = []
  active_trade = None

  print(
      f"📊 Simulating across {total_bars - start_index} historical 1M bars..."
  )

  i = start_index
  while i < total_bars:
    df_1m_slice = df_1m_full.iloc[i - 200 : i]
    current_time = df_1m_slice["datetime"].iloc[-1]
    current_bar = df_1m_full.iloc[i]

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
        rr_ratio = (
            reward_distance / risk_distance if risk_distance > 0 else 1.5
        )

        trade_pnl = (
            (risk_per_trade_usd * rr_ratio)
            if outcome == "WIN"
            else -risk_per_trade_usd
        )
        account_balance += trade_pnl

        active_trade["exit_time"] = current_time
        active_trade["outcome"] = outcome
        active_trade["pnl"] = round(trade_pnl, 2)
        trades_executed.append(active_trade)

        print(
            f"   🏁 Trade Closed [{outcome}] | PnL: ${trade_pnl:+.2f} | New"
            f" Balance: ${account_balance:.2f}"
        )

        if account_balance <= 0:
          print(
              "⚠️ ACCOUNT BLOWOUT: Balance reached $0.00. Stopping backtest."
          )
          break

        active_trade = None

      i += 1
      continue

    # --- SCAN FOR NEW SIGNALS ---
    df_15m_slice = df_15m_full[
        df_15m_full["datetime"] <= current_time
    ].tail(50)
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
    reason = analysis_result.get("reason", "No reason provided")

    if i % 500 == 0:
      print(f"[{current_time}] 🔍 Scanning... Engine Reason: {reason}")

    if decision in ["BUY", "SELL"]:
      trade_params = analysis_result.get("trade_params", {})
      entry = trade_params.get("entry")
      sl = trade_params.get("sl")
      tp = (
          trade_params.get("tp2")
          or trade_params.get("tp1")
          or trade_params.get("tp")
      )

      if entry and sl and tp and account_balance > 0:
        print(f"\n[{current_time}] 🎯 SIGNAL FOUND: {decision}")
        print(f"   • Entry: {entry} | SL: {sl} | Target TP: {tp}")

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
  print("\n==================================================")
  print("💰 FINAL ACCOUNT PERFORMANCE REPORT")
  print("==================================================")
  print(f"• Starting Balance: ${starting_balance:,.2f}")
  print(f"• Ending Balance:   ${account_balance:,.2f}")
  print(
      f"• Net Profit/Loss:"
      f" ${account_balance - starting_balance:+,.2f}"
      f" ({(account_balance - starting_balance) / starting_balance * 100:+.2f}%)"
  )
  print(f"• Total Trades:     {len(trades_executed)}")

  if len(trades_executed) > 0:
    wins = len([t for t in trades_executed if t["outcomef"] == "WIN"])
    losses = len(trades_executed) - wins
    print(f"• Win/Loss Breakdown: {wins} Wins / {losses} Losses")
    print(f"• Win Rate:         {(wins / len(trades_executed)) * 100:.2f}%")

  print("==================================================")


if __name__ == "__main__":
  run_offline_backtest()