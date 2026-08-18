import pandas as pd
import yfinance as yf


def download_and_cache_yf():
  print("==================================================")
  print(
      "🚀 DOWNLOADING HISTORICAL DATA VIA YFINANCE (NO API LIMITS)"
  )
  print("==================================================")

  # GC=F is Gold Futures on Yahoo Finance (closely tracks XAU/USD)
  symbol = "GC=F"

  print("📥 Downloading 1-minute data (last 7 days)...")
  df_1m = yf.download(symbol, period="7d", interval="1m", progress=False)
  df_1m = clean_yf_df(df_1m)
  df_1m.to_parquet("XAU_USD_1min.parquet")
  print(f"✅ Saved XAU_USD_1min.parquet ({len(df_1m)} candles)")

  print("📥 Downloading 15-minute data (last 60 days)...")
  df_15m = yf.download(symbol, period="60d", interval="15m", progress=False)
  df_15m = clean_yf_df(df_15m)
  df_15m.to_parquet("XAU_USD_15min.parquet")
  print(f"✅ Saved XAU_USD_15min.parquet ({len(df_15m)} candles)")

  print("📥 Downloading 1-hour data (history)...")
  df_1h = yf.download(symbol, period="max", interval="1h", progress=False)
  df_1h = clean_yf_df(df_1h)
  df_1h.to_parquet("XAU_USD_1h.parquet")
  print(f"✅ Saved XAU_USD_1h.parquet ({len(df_1h)} candles)")

  print("📥 Generating 4-hour data from 1-hour resample...")
  df_1h_indexed = df_1h.set_index("datetime")
  df_4h = (
      df_1h_indexed.resample("4H")
      .agg(
          {
              "open": "first",
              "high": "max",
              "low": "min",
              "close": "last",
          }
      )
      .dropna()
      .reset_index()
  )
  df_4h.to_parquet("XAU_USD_4h.parquet")
  print(f"✅ Saved XAU_USD_4h.parquet ({len(df_4h)} candles)")

  print(
      "\n🎉 All historical data cached successfully using free Yahoo Finance"
      " data!"
  )


def clean_yf_df(df):
  # Handle multi-index columns in newer yfinance versions
  if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

  df = df.reset_index()
  df.columns = [str(col).lower() for col in df.columns]

  if "date" in df.columns and "datetime" not in df.columns:
    df.rename(columns={"date": "datetime"}, inplace=True)
  elif "index" in df.columns and "datetime" not in df.columns:
    df.rename(columns={"index": "datetime"}, inplace=True)

  required_cols = ["datetime", "open", "high", "low", "close"]
  available_cols = [c for c in required_cols if c in df.columns]
  df = df[available_cols].dropna()
  return df


if __name__ == "__main__":
  download_and_cache_yf()