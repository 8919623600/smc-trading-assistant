from datetime import datetime
import os
import time
import pandas as pd
import requests
from smc_engine import SMCTradingEngine, get_current_ist_time

# ==========================================
# CONFIGURATION & ENVIRONMENT API KEYS
# ==========================================
# Pulls your existing system environment variables automatically
API_KEYS = [
    os.getenv("TWELVE_DATA_API_KEY_1"),
    os.getenv("TWELVE_DATA_API_KEY_2"),
]

# Filter out any None values just in case an env variable wasn't loaded
API_KEYS = [key for key in API_KEYS if key]

if not API_KEYS:
  raise ValueError(
      "❌ CRITICAL ERROR: No Twelve Data API keys found in environment variables (TWELVE_DATA_API_KEY_1 / TWELVE_DATA_API_KEY_2)."
  )

print(
    f"🔒 Loaded {len(API_KEYS)} API key(s) securely from system environment variables."
)

# Assets list
ASSETS = [
    {"symbol": "XAU/USD", "name": "Gold", "twelve_symbol": "XAU/USD"},
    {"symbol": "EUR/USD", "name": "Euro / US Dollar", "twelve_symbol": "EUR/USD"},
]

# Global tracker to alternate keys
current_key_index = 0


def fetch_twelve_data(symbol: str, interval: str, outputsize: int = 100):
  """Fetches data from Twelve Data using your environment API keys with automatic fallback."""
  global current_key_index

  for attempt in range(len(API_KEYS)):
    active_key = API_KEYS[current_key_index]
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize={outputsize}&apikey={active_key}&format=JSON"

    try:
      response = requests.get(url, timeout=10)
      data = response.json()

      # Check if API returned a rate limit or key error
      if "code" in data and data["code"] in [429, 401, 403]:
        print(
            f"      [Key Switch] Key index {current_key_index} hit limit/auth"
            " issue. Rotating key..."
        )
        current_key_index = (current_key_index + 1) % len(API_KEYS)
        continue

      if "values" in data:
        df = pd.DataFrame(data["values"])
        # Reverse array to chronological order for SMC calculations
        df = df.iloc[::-1].reset_index(drop=True)

        for col in ["open", "high", "low", "close"]:
          if col in df.columns:
            df[col] = df[col].astype(float)

        df["datetime"] = pd.to_datetime(df["datetime"])
        return df
      else:
        print(f"      [API Note] {symbol} ({interval}): {data.get('message', data)}")
        return None

    except requests.exceptions.Timeout:
      print(f"      [Error] Timeout fetching {symbol} ({interval}) with key index {current_key_index}.")
      current_key_index = (current_key_index + 1) % len(API_KEYS)
    except Exception as e:
      print(f"      [Error] Exception fetching {symbol} ({interval}): {str(e)}")
      return None

  return None


def run_scanner_loop():
  print("==================================================")
  print("🚀 STARTING INSTITUTIONAL SMC SCANNER ENGINE")
  print("==================================================")

  engine = SMCTradingEngine(min_rr=2.0, max_rr=8.0, atr_multiplier=0.4)

  while True:
    for asset in ASSETS:
      symbol = asset["symbol"]
      name = asset["name"]
      twelve_symbol = asset["twelve_symbol"]

      print(f"\n🎯 PROCESSING: {symbol} ({name})")
      print(f"⏰ Time (IST): {get_current_ist_time()}")

      try:
        print("   ├── Fetching 4H macro context...")
        df_4h = fetch_twelve_data(twelve_symbol, "4h", outputsize=50)
        time.sleep(6)  # Pause to respect free-tier rate limits

        print("   ├── Fetching 1H liquidity timeframe...")
        df_1h = fetch_twelve_data(twelve_symbol, "1h", outputsize=50)
        time.sleep(6)

        print("   ├── Fetching 15M structure & POI timeframe...")
        df_15m = fetch_twelve_data(twelve_symbol, "15min", outputsize=50)
        time.sleep(6)

        print("   ├── Fetching 1M execution timeframe...")
        df_1m = fetch_twelve_data(twelve_symbol, "1min", outputsize=50)

        # Validate that all timeframes are present
        if df_4h is None or df_1h is None or df_15m is None or df_1m is None:
          print("   └── ⚠️ Status: Skipped (Incomplete data package received from API).")
          print("==================================================")
          continue

        # Bundle data for the state machine
        data_dict = {"4H": df_4h, "1H": df_1h, "15M": df_15m, "1M": df_1m}

        # Run state machine evaluation
        analysis_result = engine.analyze(data_dict)

        decision = analysis_result["decision"]
        reason_msg = analysis_result.get("reason", decision)
        
        print(f"   ├── 4H Macro Bias: {analysis_result.get('bias_4h', 'ANALYZING...')}")
        print(f"   ├── 1H Liquidity:  {analysis_result.get('liquidity_sweep', 'NONE')} Sweep")
        print(f"   └── 🚦 Engine Status: {reason_msg}")

        if decision in ["BUY", "SELL"]:
          params = analysis_result["trade_params"]
          print(f"\n   🔥 VALIDATED INSTITUTIONAL SETUP FOUND: {decision} 🔥")
          print(f"      Entry Price: {params['entry']}")
          print(f"      Stop Loss:   {params['sl']}")
          print(f"      Target 1:    {params['tp1']}")
          print(f"      Target 2:    {params['tp2']}")
          print(f"      Risk/Reward: {params['rr']}R")

      except Exception as e:
        print(f"   └── ⚠️ Runtime Error: {str(e)}")

      print("==================================================")

    print("💤 Cycle complete. Resting before next institutional check...\n")
    time.sleep(30)


if __name__ == "__main__":
  run_scanner_loop()