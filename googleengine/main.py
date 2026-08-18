from datetime import datetime
import time
import pandas as pd
import requests
from smc_engine import SMCTradingEngine, get_current_ist_time

# ==========================================
# CONFIGURATION & CREDENTIALS
# ==========================================
TWELVE_DATA_API_KEY = "YOUR_TWELVEDATA_API_KEY"

# Assets list
ASSETS = [
    {"symbol": "XAU/USD", "name": "Gold", "twelve_symbol": "XAU/USD"},
    {"symbol": "EUR/USD", "name": "Euro / US Dollar", "twelve_symbol": "EUR/USD"},
]


def fetch_twelve_data(symbol: str, interval: str, outputsize: int = 100):
  """Fetches OHLCV data from Twelve Data API safely with a 10s timeout."""
  url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize={outputsize}&apikey={TWELVE_DATA_API_KEY}&format=JSON"

  try:
    response = requests.get(url, timeout=10)
    data = response.json()

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
    print(f"      [Error] Timeout fetching {symbol} ({interval}).")
    return None
  except Exception as e:
    print(f"      [Error] Exception fetching {symbol} ({interval}): {str(e)}")
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
        time.sleep(8)  # Pause to respect free-tier rate limits (8 req/min)

        print("   ├── Fetching 1H liquidity timeframe...")
        df_1h = fetch_twelve_data(twelve_symbol, "1h", outputsize=50)
        time.sleep(8)

        print("   ├── Fetching 15M structure & POI timeframe...")
        df_15m = fetch_twelve_data(twelve_symbol, "15min", outputsize=50)
        time.sleep(8)

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
          
          # Hook your Telegram/History logs here if needed:
          # send_telegram_alert(symbol, decision, params)

      except Exception as e:
        print(f"   └── ⚠️ Runtime Error: {str(e)}")

      print("==================================================")

    print("💤 Cycle complete. Resting before next institutional check...\n")
    time.sleep(30)


if __name__ == "__main__":
  run_scanner_loop()