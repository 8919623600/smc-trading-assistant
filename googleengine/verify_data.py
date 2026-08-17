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


def find_smc_swings(df: pd.DataFrame, window: int = 2):
    """Identifies verified SMC Fractal Swing Highs and Swing Lows."""
    swing_highs = []
    swing_lows = []

    for i in range(window, len(df) - window):
        # Swing High: High is greater than 'window' bars to left and right
        is_high = all(
            df["high"].iloc[i] > df["high"].iloc[i - j]
            for j in range(1, window + 1)
        ) and all(
            df["high"].iloc[i] >= df["high"].iloc[i + j]
            for j in range(1, window + 1)
        )

        if is_high:
            swing_highs.append(df["high"].iloc[i])

        # Swing Low: Low is lower than 'window' bars to left and right
        is_low = all(
            df["low"].iloc[i] < df["low"].iloc[i - j]
            for j in range(1, window + 1)
        ) and all(
            df["low"].iloc[i] <= df["low"].iloc[i + j]
            for j in range(1, window + 1)
        )

        if is_low:
            swing_lows.append(df["low"].iloc[i])

    # Fallback to recent max/min if no swing pivot is isolated
    active_sh = swing_highs[-1] if swing_highs else df["high"].max()
    active_sl = swing_lows[-1] if swing_lows else df["low"].min()

    # If the latest swing high is lower than recent price, get the highest recent swing
    if active_sh < df["close"].iloc[-1] and len(swing_highs) > 1:
        active_sh = max(swing_highs[-3:])

    return active_sh, active_sl


def inspect_market_state(symbol="XAU/USD"):
    print(f"Fetching real-time market data for '{symbol}' via Twelve Data...")

    try:
        # Fetch 500 bars of 15M data (~5 days for accurate active structure)
        ts_15m = td.time_series(
            symbol=symbol, interval="15min", outputsize=500, timezone="UTC"
        )
        df_15m = ts_15m.as_pandas()

        # Fetch 100 bars of 1M data (for live execution & quotes)
        ts_1m = td.time_series(
            symbol=symbol, interval="1min", outputsize=100, timezone="UTC"
        )
        df_1m = ts_1m.as_pandas()

        if df_15m is None or df_1m is None or df_15m.empty or df_1m.empty:
            print(f"❌ Error: No data returned for '{symbol}'.")
            return

        # Format & Convert Timezones to IST
        for df in [df_15m, df_1m]:
            df.index = pd.to_datetime(df.index)
            df.sort_index(inplace=True)
            for col in ["open", "high", "low", "close"]:
                df[col] = df[col].astype(float)

            if df.index.tz is None:
                df.index = df.index.tz_localize("UTC").tz_convert(IST)
            else:
                df.index = df.index.tz_convert(IST)

        # Resample into 1H and 4H timeframes
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

        # 1. Active 4H SMC Fractal Swing Range
        h4_high, h4_low = find_smc_swings(df_4h, window=2)
        equilibrium = (h4_high + h4_low) / 2
        bias = (
            "BEARISH (Premium Zone)"
            if current_price > equilibrium
            else "BULLISH (Discount Zone)"
        )

        # 2. 1H Liquidity Pools (BSL / SSL)
        h1_bsl, h1_ssl = find_smc_swings(df_1h, window=2)

        swept_bsl = df_1m["high"].iloc[-10:].max() >= h1_bsl
        swept_ssl = df_1m["low"].iloc[-10:].min() <= h1_ssl

        # 3. 15M POI (Fair Value Gap)
        fvg_type = "None Detected"
        fvg_range = "N/A"

        start_idx = len(df_15m) - 1
        end_idx = max(2, len(df_15m) - 15)

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

        # Output Verification
        print("\n==================================================")
        print(f"📊 LIVE SMC MARKET VERIFICATION ({symbol})")
        print(f"⏰ Bar Time (IST):    {last_time_ist}")
        print(f"💲 Current Price:    {current_price:.2f}")
        print("==================================================")
        print("1️⃣  4H SMC SWING STRUCTURE & BIAS")
        print(f"   • Active Swing High: {h4_high:.2f}")
        print(f"   • Active Swing Low:  {h4_low:.2f}")
        print(f"   • Equilibrium:       {equilibrium:.2f}")
        print(f"   • Overall Bias:      {bias}")
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