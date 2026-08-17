import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
from twelvedata import TDClient

IST = ZoneInfo("Asia/Kolkata")
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")

if not TWELVE_DATA_API_KEY:
    print("❌ Error: TWELVE_DATA_API_KEY environment variable is not set.")
    sys.exit(1)

td = TDClient(apikey=TWELVE_DATA_API_KEY)


def inspect_market_state(symbol="XAU/USD"):
    print(f"Fetching multi-day market data for '{symbol}' via Twelve Data...")

    try:
        # 1. Fetch 500 bars of 15M data (~5 days of market history for true 4H/1H structure)
        ts_15m = td.time_series(
            symbol=symbol, interval="15min", outputsize=500, timezone="UTC"
        )
        df_15m = ts_15m.as_pandas()

        # 2. Fetch 100 bars of 1M data (for precise live price & 1M entries)
        ts_1m = td.time_series(
            symbol=symbol, interval="1min", outputsize=100, timezone="UTC"
        )
        df_1m = ts_1m.as_pandas()

        if df_15m is None or df_1m is None:
            print("❌ Error fetching data.")
            return

        # Prepare 15M & 1M DataFrames
        for df in [df_15m, df_1m]:
            df.index = pd.to_datetime(df.index)
            df.sort_index(inplace=True)
            for col in ["open", "high", "low", "close"]:
                df[col] = df[col].astype(float)
            if df.index.tz is None:
                df.index = df.index.tz_localize("UTC").tz_convert(IST)
            else:
                df.index = df.index.tz_convert(IST)

        # Resample 15M data into true 1H and 4H DataFrames
        df_1h = (
            df_15m.resample("1h")
            .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
            .dropna()
        )
        df_4h = (
            df_15m.resample("4h")
            .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
            .dropna()
        )

        current_price = df_1m["close"].iloc[-1]
        last_time_ist = df_1m.index[-1].strftime("%Y-%m-%d %I:%M:%S %p IST")

        # True 4H Structure across 5 days
        h4_high = df_4h["high"].tail(20).max()
        h4_low = df_4h["low"].tail(20).min()
        equilibrium = (h4_high + h4_low) / 2
        bias = (
            "BEARISH (Premium Zone)"
            if current_price > equilibrium
            else "BULLISH (Discount Zone)"
        )

        # 1H Liquidity Pools
        h1_bsl = df_1h["high"].iloc[-24:-1].max()
        h1_ssl = df_1h["low"].iloc[-24:-1].min()

        swept_bsl = df_1m["high"].iloc[-10:].max() >= h1_bsl
        swept_ssl = df_1m["low"].iloc[-10:].min() <= h1_ssl

        print("\n==================================================")
        print(f"📊 LIVE SMC MARKET VERIFICATION ({symbol})")
        print(f"⏰ Bar Time (IST):    {last_time_ist}")
        print(f"💲 Current Price:    {current_price:.2f}")
        print("==================================================")
        print("1️⃣  4H DEALING RANGE & BIAS (5-DAY LOOKBACK)")
        print(f"   • 4H Swing High:  {h4_high:.2f}")
        print(f"   • 4H Swing Low:   {h4_low:.2f}")
        print(f"   • Equilibrium:    {equilibrium:.2f}")
        print(f"   • Overall Bias:   {bias}")
        print("--------------------------------------------------")
        print("2️⃣  1H LIQUIDITY LEVELS")
        print(f"   • Buy-Side Liquidity (BSL):  {h1_bsl:.2f}")
        print(f"   • Sell-Side Liquidity (SSL): {h1_ssl:.2f}")
        print(
            f"   • BSL Swept Recently?        {'YES 🚨' if swept_bsl else 'NO'}"
        )
        print(
            f"   • SSL Swept Recently?        {'YES 🚨' if swept_ssl else 'NO'}"
        )
        print("==================================================\n")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else "XAU/USD"
    inspect_market_state(symbol)