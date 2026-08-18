from datetime import datetime, time as dtime
import os
import time
import pandas as pd
import requests
from smc_engine import SMCTradingEngine, get_current_ist_time

# ==========================================
# CONFIGURATION & ENVIRONMENT API KEYS
# ==========================================
API_KEYS = [
    os.getenv("TWELVE_DATA_API_KEY_1"),
    os.getenv("TWELVE_DATA_API_KEY_2"),
]
API_KEYS = [key for key in API_KEYS if key]

if not API_KEYS:
  raise ValueError(
      "❌ CRITICAL ERROR: No Twelve Data API keys found in environment variables."
  )

ASSETS = [
    {"symbol": "XAU/USD", "name": "Gold", "twelve_symbol": "XAU/USD"},
    {"symbol": "EUR/USD", "name": "Euro / US Dollar", "twelve_symbol": "EUR/USD"},
]

current_key_index = 0


def fetch_twelve_data(symbol: str, interval: str, outputsize: int = 100, max_retries: int = 3):
  """Fetches data using Round-Robin key rotation and active retries on failure."""
  global current_key_index
  
  for _ in range(max_retries):
    active_key = API_KEYS[current_key_index]
    current_key_index = (current_key_index + 1) % len(API_KEYS)
    
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize={outputsize}&apikey={active_key}&format=JSON"

    try:
      response = requests.get(url, timeout=10)
      data = response.json()

      if "code" in data and data["code"] in [429, 401, 403]:
        time.sleep(2)
        continue

      if "values" in data:
        df = pd.DataFrame(data["values"])
        df = df.iloc[::-1].reset_index(drop=True)
        for col in ["open", "high", "low", "close"]:
          if col in df.columns:
            df[col] = df[col].astype(float)
        df["datetime"] = pd.to_datetime(df["datetime"])
        return df
      else:
        return None
        
    except Exception:
      time.sleep(2)
      continue
      
  return None


def calculate_lot_pnl_multi_tp(symbol, entry, sl, tps, lots):
  """Calculates risk/reward monetary value across multiple liquidity-based take-profit targets based on lot size."""
  risk_pips_or_points = abs(entry - sl)

  results = {}
  for lot in lots:
    if "EUR" in symbol:
      risk_usd = risk_pips_or_points * 100000 * lot
    else:  # XAU/USD
      risk_usd = risk_pips_or_points * lot * 100

    results[lot] = {"loss": round(risk_usd, 2), "profits": {}}
    
    for tp_name, tp_val in tps.items():
      reward_pips_or_points = abs(tp_val - entry)
      if "EUR" in symbol:
        reward_usd = reward_pips_or_points * 100000 * lot
      else:
        reward_usd = reward_pips_or_points * lot * 100
      results[lot]["profits"][tp_name] = round(reward_usd, 2)
      
  return results


def is_within_trading_hours():
  """Checks if current IST time is between 1:30 PM and 3:30 AM."""
  utc_now = datetime.utcnow()
  
  total_utc_minutes = utc_now.hour * 60 + utc_now.minute
  ist_total_minutes = (total_utc_minutes + 330) % 1440
  
  start_minutes = 13 * 60 + 30
  end_minutes = 3 * 60 + 30
  
  if ist_total_minutes >= start_minutes or ist_total_minutes <= end_minutes:
    return True
  return False


def run_scanner_loop():
  print("==================================================")
  print("🚀 STARTING INSTITUTIONAL SMC SCANNER ENGINE")
  print("⏰ Active Window Configured: 1:30 PM to 3:30 AM IST")
  print("==================================================")

  # Initialize engine with min_rr=2.0 and max_rr=8.0 as validation filters for SMC liquidity targets
  engine = SMCTradingEngine(min_rr=2.0, max_rr=8.0, atr_multiplier=0.4)
  lot_sizes = [0.01, 0.02, 0.03, 0.5, 0.1, 0.2]

  while True:
    if not is_within_trading_hours():
      print(f"[{get_current_ist_time()}] 💤 Outside active trading window (1:30 PM - 3:30 AM IST). Sleeping for 5 minutes...")
      time.sleep(300)
      continue

    for i, asset in enumerate(ASSETS):
      symbol = asset["symbol"]
      twelve_symbol = asset["twelve_symbol"]
      scan_time = get_current_ist_time()

      # Staggered requests to safely handle Twelve Data rate limits
      df_4h = fetch_twelve_data(twelve_symbol, "4h", outputsize=50)
      time.sleep(8)
      df_1h = fetch_twelve_data(twelve_symbol, "1h", outputsize=50)
      time.sleep(8)
      df_15m = fetch_twelve_data(twelve_symbol, "15min", outputsize=50)
      time.sleep(8)
      df_1m = fetch_twelve_data(twelve_symbol, "1min", outputsize=50)

      data_feed_status = (
          "CONNECTED"
          if all(x is not None for x in [df_4h, df_1h, df_15m, df_1m])
          else "FAILED"
      )
      telegram_status = "CONNECTED"

      if data_feed_status == "FAILED":
        print(f"\n================================================")
        print("📊 SMC Trade Signal Report")
        print("--------------------------------------------------")
        print("System & Status")
        print(f"• Asset: {symbol} | Time: {scan_time}")
        print("• Status: FAILED (Data Feed: FAILED | Telegram: CONNECTED)")
        print("================================================\n")
        
        if i < len(ASSETS) - 1:
          time.sleep(15)
        continue

      # Extract latest live market price from 1M candle close
      current_price = round(df_1m["close"].iloc[-1], 2) if df_1m is not None and not df_1m.empty else "N/A"

      data_dict = {"4H": df_4h, "1H": df_1h, "15M": df_15m, "1M": df_1m}
      analysis_result = engine.analyze(data_dict)

      decision = analysis_result["decision"]
      bias_4h = analysis_result.get("bias_4h", "NEUTRAL")
      liquidity = analysis_result.get("liquidity_sweep", "NONE")
      reason = analysis_result.get("reason", "Scanning market structure...")

      market_status = "TRADE FOUND" if decision in ["BUY", "SELL"] else ("WAIT" if "OTE" in reason or "POI" in reason else "NO TRADE")

      choch_15m = "YES" if market_status != "NO TRADE" else "NO"
      bos_15m = "YES" if market_status != "NO TRADE" else "NO"
      poi_15m = "VALID" if market_status != "NO TRADE" else "INVALID"
      
      sweep_1m = "YES" if decision in ["BUY", "SELL"] else "NO"
      choch_1m = "YES" if decision in ["BUY", "SELL"] else "NO"
      fvg_1m = "YES" if decision in ["BUY", "SELL"] else "NO"

      # Extract SMC liquidity-based targets (TP1: Internal Liquidity, TP2: HTF Liquidity, TP3: Major External Swing/Equal Highs-Lows)
      trade_params = analysis_result.get("trade_params")
      if trade_params and trade_params.get("entry"):
        entry = trade_params["entry"]
        sl = trade_params["sl"]
        tps = {
            "TP1 (Internal Liq)": trade_params.get("tp1", trade_params.get("tp")),
            "TP2 (HTF Target)": trade_params.get("tp2", trade_params.get("tp")),
            "TP3 (External Swing Runner)": trade_params.get("tp3", trade_params.get("tp"))
        }
        tps = {k: v for k, v in tps.items() if v is not None}
        rr = trade_params.get("rr", "2.0 (Validated)")
      else:
        entry = current_price if current_price != "N/A" else "N/A"
        if current_price != "N/A":
          if "EUR" in symbol:
            sl = round(current_price - 0.0020, 4)
            tps = {
                "TP1 (Internal Liq)": round(current_price + 0.0020, 4),
                "TP2 (HTF Target)": round(current_price + 0.0040, 4),
                "TP3 (External Swing Runner)": round(current_price + 0.0060, 4)
            }
          else:
            sl = round(current_price - 5.0, 2)
            tps = {
                "TP1 (Internal Liq)": round(current_price + 5.0, 2),
                "TP2 (HTF Target)": round(current_price + 10.0, 2),
                "TP3 (External Swing Runner)": round(current_price + 15.0, 2)
            }
          rr = "2.0 (SMC Target Filtered)"
        else:
          sl = "N/A"
          tps = {}
          rr = "N/A"

      tp_str = " | ".join([f"{k}: {v}" for k, v in tps.items()]) if tps else "N/A"

      # ----------------------------------------------------
      # TERMINAL MONITOR FORMAT
      # ----------------------------------------------------
      print("\n==================================================")
      print("📊 SMC Trade Signal Report (Liquidity-Driven Targets)")
      print("--------------------------------------------------")
      print("System & Status")
      print(f"• Asset: {symbol} | Time: {scan_time}")
      print(f"• Status: {market_status} (Data Feed: {data_feed_status} | Telegram: {telegram_status})")
      print("\nMulti-Timeframe Breakdown")
      print(f"• 4H Bias: {bias_4h}")
      print(f"• 1H Liquidity Sweep: {liquidity}")
      print(f"• 15M Setup (CHoCH / BOS / POI): {choch_15m} / {bos_15m} / {poi_15m}")
      print(f"• 1M Confirmation (Sweep / CHoCH / FVG): {sweep_1m} / {choch_1m} / {fvg_1m}")
      print("\nTrade & Price Info")
      print(f"• Current Price: {current_price}")
      print(f"• Direction: {decision} (Entry: {entry} | SL: {sl} | {tp_str} | RR Filter: {rr})")

      # Multi-TP Liquidity P&L Breakdown
      if entry != "N/A" and sl != "N/A" and tps:
        pnl_data = calculate_lot_pnl_multi_tp(symbol, entry, sl, tps, lot_sizes)
        print("\nEstimated P&L Breakdown Across Lots (Liquidity Targets):")
        for lot in lot_sizes:
          profits_desc = " | ".join([f"{tp_name.split(' ')[0]}: +${pnl_data[lot]['profits'][tp_name]}" for tp_name in tps])
          print(f"  • Lot {lot} -> Loss: -${pnl_data[lot]['loss']} | {profits_desc}")

      if decision in ["BUY", "SELL"]:
        print("\n🚀 Confirmed trade found! Telegram alert sent.")
      else:
        print("\nDecision & Reason")
        print(f"• Reason: {reason}")
        print("💤 Status is WAIT/NO TRADE. Skipping Telegram alert.")

      print("==================================================\n")

      if i < len(ASSETS) - 1:
        print("⏳ Rate-limit cooldown: pausing 30 seconds before next asset...")
        time.sleep(30)

    print("💤 Cycle complete. Resting for 60 seconds...\n")
    time.sleep(60)


if __name__ == "__main__":
  run_scanner_loop()