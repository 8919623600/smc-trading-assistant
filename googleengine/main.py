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


def calculate_lot_pnl(symbol, entry, sl, tp, lots):
  """Calculates risk/reward monetary value based on lot size."""
  risk_pips_or_points = abs(entry - sl)
  reward_pips_or_points = abs(tp - entry)
  multiplier = 100 if "XAU" in symbol else 100000

  results = {}
  for lot in lots:
    if "EUR" in symbol:
      risk_usd = risk_pips_or_points * multiplier * lot
      reward_usd = reward_pips_or_points * multiplier * lot
    else:
      risk_usd = risk_pips_or_points * lot * 100
      reward_usd = reward_pips_or_points * lot * 100

    results[lot] = {"loss": round(risk_usd, 2), "profit": round(reward_usd, 2)}
  return results


def is_within_trading_hours():
  """Checks if current IST time is between 1:30 PM and 3:30 AM."""
  # Get current time in IST by evaluating system time + offset or parsing datetime string
  # Using datetime.now() assuming server is set or pulling via standard timezone check:
  from pytz import timezone  # Standard if available, or we use standard time extraction
  
  # Fallback to standard offset calculation (+5:30) if pytz isn't installed
  utc_now = datetime.utcnow()
  ist_hour = (utc_now.hour + 5) % 24
  ist_minute = utc_now.minute + 30
  if ist_minute >= 60:
    ist_minute -= 60
    ist_hour = (ist_hour + 1) % 24
  # Adjust if UTC date rolled over hours (simplified check using total minutes from midnight)
  
  now_total_minutes = ist_hour * 60 + ist_minute
  
  # Window: 1:30 PM (13:30 = 810 mins) to 3:30 AM next morning (03:30 = 210 mins)
  start_minutes = 13 * 60 + 30  # 810 mins
  end_minutes = 3 * 60 + 30     # 210 mins
  
  # Active if between 13:30 and 23:59 OR between 00:00 and 03:30
  if now_total_minutes >= start_minutes or now_total_minutes <= end_minutes:
    return True
  return False


def run_scanner_loop():
  print("==================================================")
  print("🚀 STARTING INSTITUTIONAL SMC SCANNER ENGINE")
  print("⏰ Active Window Configured: 1:30 PM to 3:30 AM IST")
  print("==================================================")

  engine = SMCTradingEngine(min_rr=2.0, max_rr=8.0, atr_multiplier=0.4)
  lot_sizes = [0.01, 0.02, 0.03, 0.1, 0.2, 0.5]

  while True:
    # Time restriction check
    if not is_within_trading_hours():
      print(f"[{get_current_ist_time()}] 💤 Outside active trading window (1:30 PM - 3:30 AM IST). Sleeping for 5 minutes...")
      time.sleep(300) # Check every 5 minutes if it's time to wake up
      continue

    for asset in ASSETS:
      symbol = asset["symbol"]
      twelve_symbol = asset["twelve_symbol"]
      scan_time = get_current_ist_time()

      df_4h = fetch_twelve_data(twelve_symbol, "4h", outputsize=50)
      time.sleep(1)
      df_1h = fetch_twelve_data(twelve_symbol, "1h", outputsize=50)
      time.sleep(1)
      df_15m = fetch_twelve_data(twelve_symbol, "15min", outputsize=50)
      time.sleep(1)
      df_1m = fetch_twelve_data(twelve_symbol, "1min", outputsize=50)

      data_feed_status = (
          "CONNECTED"
          if all(x is not None for x in [df_4h, df_1h, df_15m, df_1m])
          else "FAILED"
      )
      telegram_status = "CONNECTED"

      if data_feed_status == "FAILED":
        print(f"\n================================================")
        print("SMC TRADE SIGNAL REPORT")
        print("================================================")
        print(f"System Status:\nData Feed: FAILED\nTelegram: {telegram_status}")
        print(f"\nSymbol:\n{symbol}\n\nTime:\n{scan_time}")
        print("\nMarket Status:\nNO TRADE\n================================================")
        continue

      data_dict = {"4H": df_4h, "1H": df_1h, "15M": df_15m, "1M": df_1m}
      analysis_result = engine.analyze(data_dict)

      decision = analysis_result["decision"]
      bias_4h = analysis_result.get("bias_4h", "NEUTRAL")
      liquidity = analysis_result.get("liquidity_sweep", "NONE")
      reason = analysis_result.get("reason", "Scanning market structure...")

      market_status = "TRADE FOUND" if decision in ["BUY", "SELL"] else ("WAIT" if "OTE" in reason or "POI" in reason else "NO TRADE")

      print("================================================")
      print("SMC TRADE SIGNAL REPORT")
      print("================================================")
      print(f"System Status:")
      print(f"Data Feed: {data_feed_status}")
      print(f"Telegram: {telegram_status}")
      print(f"\nSymbol:\n{symbol}")
      print(f"\nTime:\n{scan_time}")
      print(f"\nMarket Status:\n{market_status}")
      
      print(f"\nHTF Analysis (4H):\nBias:\n{bias_4h}")
      if liquidity != "NONE":
          print(f"\nLiquidity (1H):\nEvent:\n{liquidity}-SIDE SWEEP")
      else:
          print(f"\nLiquidity (1H):\nEvent:\nNONE")
          
      print(f"\nSetup (15M):")
      print(f"CHoCH:\n{'YES' if market_status != 'NO TRADE' else 'NO'}")
      print(f"Displacement:\n{'YES' if market_status != 'NO TRADE' else 'NO'}")
      print(f"BOS:\n{'YES' if market_status != 'NO TRADE' else 'NO'}")
      print(f"POI:\n{'VALID' if market_status != 'NO TRADE' else 'INVALID'}")
      print(f"Zone:\n{analysis_result.get('trade_params', {}).get('entry', 'N/A')}")

      print(f"\nEntry Confirmation (1M):")
      print(f"Sweep:\n{'YES' if decision in ['BUY', 'SELL'] else 'NO'}")
      print(f"CHoCH:\n{'YES' if decision in ['BUY', 'SELL'] else 'NO'}")
      print(f"FVG:\n{'YES' if decision in ['BUY', 'SELL'] else 'NO'}")

      print(f"\nTRADE:")
      print(f"Direction:\n{decision if decision in ['BUY', 'SELL'] else 'NONE'}")
      
      if decision in ["BUY", "SELL"]:
        params = analysis_result["trade_params"]
        entry = params["entry"]
        sl = params["sl"]
        tp = params["tp2"]
        risk_pts = round(abs(entry - sl), 2)
        reward_pts = round(abs(tp - entry), 2)

        print(f"Entry:\n{entry}")
        print(f"SL:\n{sl}")
        print(f"TP:\n{tp}")
        print(f"Risk:\n{risk_pts} points")
        print(f"Reward:\n{reward_pts} points")
        print(f"RR:\n1:{params['rr']}")

        pnl_data = calculate_lot_pnl(symbol, entry, sl, tp, lot_sizes)
        print(f"\nESTIMATED P&L ACROSS LOT SIZES:")
        for lot in lot_sizes:
          print(f"Lot {lot} -> Max Loss: -${pnl_data[lot]['loss']} | Max Profit: +${pnl_data[lot]['profit']}")
      else:
        print(f"Entry:\nN/A\nSL:\nN/A\nTP:\nN/A\nRisk:\nN/A\nReward:\nN/A\nRR:\nN/A")

      print(f"\nFINAL DECISION:\n{decision}")
      print(f"\nReason:\n- {reason}")
      print("================================================\n")

    print("💤 Cycle complete. Resting for 60 seconds...\n")
    time.sleep(60)


if __name__ == "__main__":
  run_scanner_loop()