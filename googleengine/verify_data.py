import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
from twelvedata import TDClient

# Global Timezone & API Setup
IST = ZoneInfo("Asia/Kolkata")
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")

if not TWELVE_DATA_API_KEY:
    print("❌ Error: TWELVE_DATA_API_KEY environment variable is not set.")
    print("Run: export TWELVE_DATA_API_KEY='your_api_key'")
    sys.exit(1)

td = TDClient(apikey=TWELVE_DATA_API_KEY)


def inspect_market_state(symbol="XAU/USD"):
    print(f"Fetching real-time data for '{symbol}' via Twelve Data...")

    try:
        ts = td.time_series(symbol=symbol, interval="1min", outputsize=500)
        df_1m = ts.as_pandas()

        if df_1m is None or df_1m.empty:
            print(
                f"❌ Error: No data returned for '{symbol}'. Verify symbol or API key limits."
            )
            return

        # Sort index chronologically (newest at bottom)
        df_1m = df_1m.sort_index()

        for col in ["open", "high", "low", "close"]:
            df_1m[col] = df_1m[col].astype(float)

        # Convert Datetime Index to IST
        if df_1m.index.tz is None:
            df_1m.index = df_1m.index.tz_localize("UTC").tz_convert(IST)
        else:
            df_1m.index = df_1m.index.tz_convert(IST)

        # Resample into higher timeframes locally
        df_15m = (
            df_1m.resample("15min")
            .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
            .dropna()
        )
        df_1h = (
            df_1m.resample("1h")
            .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
            .dropna()
        )
        df_4h = (
            df_1m.resample("4h")
            .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
            .dropna()
        )

        current_price = df_1m["close"].iloc[-1]
        last_time_ist = df_1m.index[-1].strftime("%Y-%m-%d %I:%M:%S %p IST")

        # 1. 4H Structure & Dealing Range
        h4_high = df_4h["high"].tail(20).max()
        h4_low = df_4h["low"].tail(20).min()
        equilibrium = (h4_high + h4_low) / 2
        bias = (
            "BEARISH (Premium Zone)"
            if current_price > equilibrium
            else "BULLISH (Discount Zone)"
        )

        # 2. 1H Liquidity Pools
        h1_bsl = df_1h["high"].iloc[-11:-1].max()
        h1_ssl = df_1h["low"].iloc[-11:-1].min()

        swept_bsl = df_1m["high"].iloc[-10:].max() >= h1_bsl
        swept_ssl = df_1m["low"].iloc[-10:].min() <= h1_ssl

        # 3. 15M POI (Fair Value Gap)
        fvg_type = "None Detected"
        fvg_range = "N/A"

        start_idx = len(df_15m) - 1
        end_idx = max(2, len(df_15m) - 10)

        for i in range(start_idx, end_idx, -1):
            if df_15m["low"].iloc[i] > df_15m["high"].iloc[i - 2]:
                fvg_type = "Bullish FVG (Demand Zone)"
                fvg_range = (
                    f"{df_15m['high'].iloc[i-2]:.2f} - {df_15m['low'].iloc[i]:.2f}"
                )
                break
            elif df_15m["high"].iloc[i] < df_15m["low"].iloc[i - 2]:
                fvg_type = "Bearish FVG (Supply Zone)"
                fvg_range = (
                    f"{df_15m['high'].iloc[i]:.2f} - {df_15m['low'].iloc[i-2]:.2f}"
                )
                break

        # Output Market Verification
        print("\n==================================================")
        print(f"📊 LIVE SMC MARKET VERIFICATION ({symbol})")
        print(f"⏰ Bar Time (IST):    {last_time_ist}")
        print(f"💲 Current Price:    {current_price:.2f}")
        print("==================================================")
        print("1️⃣  4H DEALING RANGE & BIAS")
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
        print("--------------------------------------------------")
        print("3️⃣  15M POI (FAIR VALUE GAP / OB)")
        print(f"   • Active Imbalance: {fvg_type}")
        print(f"   • FVG Price Zone:   {fvg_range}")
        print("--------------------------------------------------")
        print("4️⃣  ACTIONABLE EXECUTION PLAN")
        if current_price > equilibrium:
            print(
                f"   • PLAN: IF price sweeps 1H BSL High ({h1_bsl:.2f}) and rejects,"
            )
            print(
                f"           THEN watch for 1M Bearish CHoCH to SHORT down to {equilibrium:.2f}."
            )
        else:
            print(
                f"   • PLAN: IF price sweeps 1H SSL Low ({h1_ssl:.2f}) and holds,"
            )
            print(
                f"           THEN watch for 1M Bullish CHoCH to LONG up to {equilibrium:.2f}."
            )
        print("==================================================\n")

    except Exception as e:
        print(f"❌ Error fetching data: {e}")


if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else "XAU/USD"
    inspect_market_state(symbol)