from datetime import datetime
import os
import pandas as pd
import requests

# ==========================================
# CONFIGURATION & API KEYS
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


def download_and_cache(symbol, interval, outputsize=5000):
  url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize={outputsize}&apikey={API_KEYS[0]}&format=JSON"

  print(f"📥 Downloading {interval} data for {symbol}...")
  response = requests.get(url, timeout=15)
  data = response.json()

  if "values" in data:
    df = pd.DataFrame(data["values"])
    df = df.iloc[::-1].reset_index(drop=True)
    for col in ["open", "high", "low", "close"]:
      if col in df.columns:
        df[col] = df[col].astype(float)
    df["datetime"] = pd.to_datetime(df["datetime"])

    # Clean symbol name for filename (e.g., XAU/USD -> XAU_USD)
    clean_symbol = symbol.replace("/", "_")
    filename = f"{clean_symbol}_{interval}.parquet"

    # Save inside the current folder
    df.to_parquet(filename)
    print(f"✅ Successfully saved: {filename} ({len(df)} candles)")
  else:
    print(f"❌ Failed to fetch {interval} for {symbol}: {data}")


if __name__ == "__main__":
  print("==================================================")
  print("🚀 DOWNLOADING HISTORICAL DATA FOR BACKTESTING")
  print("==================================================")

  # Fetching XAU/USD across required timeframes
  # Note: 5000 1min candles cover roughly ~3.5 days of active trading minutes.
  # Adjust outputsize or use date ranges if you need a deeper history window.
  target_symbol = "XAU/USD"

  download_and_cache(target_symbol, "1min", outputsize=5000)
  download_and_cache(target_symbol, "15min", outputsize=1000)
  download_and_cache(target_symbol, "1h", outputsize=500)
  download_and_cache(target_symbol, "4h", outputsize=200)

  print("\n🎉 Download complete! You can now run your backtest script.")