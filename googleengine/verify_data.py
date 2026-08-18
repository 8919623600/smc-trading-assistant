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
        is_high = all(
            df["high"].iloc[i] > df["high"].iloc[i - j]
            for j in range(1, window + 1)
        ) and all(
            df["high"].iloc[i] >= df["high"].iloc[i + j]
            for j in range(1, window + 1)
        )
        if is_high:
            swing_highs.append((df.index[i], df["high"].iloc[i]))

        is_low = all(
            df["low"].iloc[i] < df["low"].iloc[i - j]
            for j in range(1, window + 1)
        ) and all(
            df["low"].iloc[i] <= df["low"].iloc[i + j]
            for j in range(1, window + 1)
        )
        if is_low:
            swing_lows.append((df.index[i], df["low"].iloc[i]))

    active_sh = swing_highs[-1][1] if swing_highs else df["high"].max()
    active_sl = swing_lows[-1][1] if swing_lows else df["low"].min()

    return active_sh, active_sl


def check_displacement(df_15m: pd.DataFrame) -> bool:
    """UPGRADE C: Validates if the most recent impulse move features strong displacement.
    Checks if the last breaking candle's body size is significantly larger than the average range.
    """
    if len(df_15m) < 10:
        return True

    # Calculate candle bodies and average body size
    bodies = (df_15m["close"] - df_15m["open"]).abs()
    avg_body = bodies.iloc[-15:-1].mean()
    latest_body = bodies.iloc[-1]

    # True displacement requires the latest structural move candle to be at least 1.3x average body size
    return latest_body >= (1.3 * avg_body)


def inspect_market_state(symbol="XAU/USD"):
    print(f"Fetching real-time market data for '{symbol}' via Twelve Data...")

    try:
        ts_15m = td.time_series(
            symbol=symbol, interval="15min", outputsize=500, timezone="UTC"
        )
        df_15m = ts_15m.as_pandas()

        ts_1m = td.time_series(
            symbol=symbol, interval="1min", outputsize=100, timezone="UTC"
        )
        df_1m = ts_1m.as_pandas()

        if df_15m is None or df_1m is None or df_15m.empty or df_1m.empty:
            print(f"❌ Error: No data returned for '{symbol}'.")
            return

        for df in [df_15m, df_1m]:
            df.index = pd.to_datetime(df.index)
            df.sort_index(inplace=True)
            for col in ["open", "high", "low", "close"]:
                df[col] = df[col].astype(float)

            if df.index.tz is None:
                df.index = df.index.tz_localize("UTC").tz_convert(IST)
            else:
                df.index = df.index.tz_convert(IST)

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

        # 1. 4H Range & UPGRADE B: Optimal Trade Entry (OTE 0.618 - 0.79 zone)
        h4_high, h4_low = find_smc_swings(df_4h, window=2)
        total_range = h4_high - h4_low

        # Calculate OTE Zones depending on direction
        # Bullish Discount OTE: retracement down to 61.8% - 79% from the high
        ote_bullish_high = h4_high - (total_range * 0.618)
        ote_bullish_low = h4_high - (total_range * 0.790)

        # Bearish Premium OTE: retracement up to 61.8% - 79% from the low
        ote_bearish_low = h4_low + (total_range * 0.618)
        ote_bearish_high = h4_low + (total_range * 0.790)

        equilibrium = (h4_high + h4_low) / 2
        bias = (
            "BEARISH (Premium Zone)"
            if current_price > equilibrium
            else "BULLISH (Discount Zone)"
        )

        # Check if price is specifically inside the institutional OTE sweet spot
        in_bullish_ote = ote_bullish_low <= current_price <= ote_bullish_high
        in_bearish_ote = ote_bearish_low <= current_price <= ote_bearish_high

        # 2. 1H Liquidity Pools
        h1_bsl, h1_ssl = find_smc_swings(df_1h, window=2)
        swept_bsl = df_1m["high"].iloc[-10:].max() >= h1_bsl
        swept_ssl = df_1m["low"].iloc[-10:].min() <= h1_ssl

        # 3. UPGRADE C: Displacement Check on 15M
        has_displacement = check_displacement(df_15m)

        # 4. 15M POI Detection
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
        print(f"📊 UPGRADED SMC MARKET VERIFICATION ({symbol})")
        print(f"⏰ Bar Time (IST):    {last_time_ist}")
        print(f"💲 Current Price:    {current_price:.2f}")
        print("==================================================")
        print("1️⃣  4H SMC RANGE & OTE ZONE (Upgrade B)")
        print(f"   • Active Swing High: {h4_high:.2f}")
        print(f"   • Active Swing Low:  {h4_low:.2f}")
        print(f"   • Equilibrium (50%): {equilibrium:.2f}")
        if bias.startswith("BULLISH"):
            print(
                f"   • 61.8% - 79% OTE Zone: {ote_bullish_low:.2f} - {ote_bullish_high:.2f}"
            )
            print(
                f"   • Price in OTE Sweet Spot? {'YES ✅ (High Confluence)' : 'NO (Waiting for deep retracement)' if not in_bullish_ote else 'YES ✅'}"
            )
        else:
            print(
                f"   • 61.8% - 79% OTE Zone: {ote_bearish_low:.2f} - {ote_bearish_high:.2f}"
            )
            print(
                f"   • Price in OTE Sweet Spot? {'YES ✅' if in_bearish_ote else 'NO (Waiting for deep retracement)'}"
            )
        print("--------------------------------------------------")
        print("2️⃣  1H LIQUIDITY POOLS")
        print(f"   • Buy-Side Liquidity (BSL):  {h1_bsl:.2f}")
        print(f"   • Sell-Side Liquidity (SSL): {h1_ssl:.2f}")
        print(
            f"   • BSL Swept Recently?        {'YES 🚨' if swept_bsl else 'NO'}"
        )
        print(
            f"   • SSL Swept Recently?        {'YES 🚨' if swept_ssl else 'NO'}"
        )
        print("--------------------------------------------------")
        print("3️⃣  DISPLACEMENT & MOMENTUM FILTER (Upgrade C)")
        print(
            f"   • Strong Impulse Detected?:  {'YES 🚀 (Institutional Expansion)' if has_displacement else 'NO ⚠️ (Weak / Choppy Move)'}"
        )
        print(f"   • Active Imbalance:          {fvg_type}")
        print(f"   • FVG Price Zone:            {fvg_range}")
        print("--------------------------------------------------")
        print("4️⃣  ACTIONABLE UPGRADED EXECUTION PLAN")
        if current_price > equilibrium:
            print(
                f"   • PLAN: Requires 1H BSL sweep AND valid Bearish CHoCH with strong displacement."
            )
            if not has_displacement:
                print(
                    "   • STATUS: 🛑 BLOCKED - Current market lacks institutional displacement momentum."
                )
        else:
            print(
                f"   • PLAN: Requires 1H SSL sweep ({h1_ssl:.2f}) down into the OTE Zone, followed by 1M Bullish CHoCH."
            )
            if not has_displacement:
                print(
                    "   • STATUS: 🛑 BLOCKED - Waiting for a high-momentum expansion candle to confirm intent."
                )
        print("==================================================\n")


if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else "XAU/USD"
    inspect_market_state(symbol)