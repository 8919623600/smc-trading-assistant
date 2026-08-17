import os
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
from twelvedata import TDClient
from googlesmc import SMCTradingEngine

# ==========================================
# ENVIRONMENT & CONFIGURATION
# ==========================================
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")

if not TWELVE_DATA_API_KEY:
    print("❌ Error: TWELVE_DATA_API_KEY environment variable is not set.")
    print("Ensure you ran: export TWELVE_DATA_API_KEY='your_api_key'")
    sys.exit(1)

# Single Target Asset & Parameters
TICKERS = ["XAU/USD"]
SCAN_INTERVAL_SECONDS = 60
SL_BUFFER = 6.00  # $6.00 buffer (60 pips) to prevent prematurely getting stopped out
IST = ZoneInfo("Asia/Kolkata")

td = TDClient(apikey=TWELVE_DATA_API_KEY)


def find_smc_swings(df: pd.DataFrame, window: int = 2):
    """Identifies verified SMC Fractal Swing Highs and Swing Lows."""
    swing_highs = []
    swing_lows = []

    for i in range(window, len(df) - window):
        is_high = all(
            df["high"].iloc[i] > df["high"].iloc[i - j] for j in range(1, window + 1)
        ) and all(
            df["high"].iloc[i] >= df["high"].iloc[i + j] for j in range(1, window + 1)
        )
        if is_high:
            swing_highs.append(df["high"].iloc[i])

        is_low = all(
            df["low"].iloc[i] < df["low"].iloc[i - j] for j in range(1, window + 1)
        ) and all(
            df["low"].iloc[i] <= df["low"].iloc[i + j] for j in range(1, window + 1)
        )
        if is_low:
            swing_lows.append(df["low"].iloc[i])

    active_sh = swing_highs[-1] if swing_highs else df["high"].max()
    active_sl = swing_lows[-1] if swing_lows else df["low"].min()

    if active_sh < df["close"].iloc[-1] and len(swing_highs) > 1:
        active_sh = max(swing_highs[-3:])

    return active_sh, active_sl


def fetch_realtime_data(symbol: str) -> dict:
    """Fetches real-time multi-timeframe data via Twelve Data in UTC and converts to IST."""
    ts_15m = td.time_series(symbol=symbol, interval="15min", outputsize=500, timezone="UTC")
    df_15m = ts_15m.as_pandas()

    ts_1m = td.time_series(symbol=symbol, interval="1min", outputsize=100, timezone="UTC")
    df_1m = ts_1m.as_pandas()

    if df_15m is None or df_1m is None or df_15m.empty or df_1m.empty:
        raise ValueError(f"No data returned from Twelve Data for '{symbol}'")

    for df in [df_15m, df_1m]:
        df.index = pd.to_datetime(df.index)
        df.sort_index(inplace=True)
        for col in ["open", "high", "low", "close"]:
            df[col] = df[col].astype(float)

        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC").tz_convert(IST)
        else:
            df.index = df.index.tz_convert(IST)

    df_1h = df_15m.resample("1h").agg({
        "open": "first", "high": "max", "low": "min", "close": "last"
    }).dropna()

    df_4h = df_15m.resample("4h").agg({
        "open": "first", "high": "max", "low": "min", "close": "last"
    }).dropna()

    return {"4H": df_4h, "1H": df_1h, "15M": df_15m, "1M": df_1m}


def run_scanner():
    engine = SMCTradingEngine(min_rr=2.0, max_rr=8.0, atr_multiplier=1.0)

    print("==================================================")
    print("   SMC GOLD REAL-TIME SCANNER (TWELVE DATA - IST) ")
    print("==================================================")

    while True:
        now_ist = datetime.now(IST).strftime("%Y-%m-%d %I:%M:%S %p IST")

        for symbol in TICKERS:
            try:
                data = fetch_realtime_data(symbol)

                # Higher Timeframe Levels
                h4_sh, h4_sl = find_smc_swings(data["4H"], window=2)
                eq_4h = (h4_sh + h4_sl) / 2

                h1_bsl, h1_ssl = find_smc_swings(data["1H"], window=2)

                result = engine.analyze(data)

                decision = result.get("decision", "NO_TRADE")
                reason = result.get("reason", "Setup validated")
                bias = result.get("bias_4h", "N/A")
                latest_price = data["1M"]["close"].iloc[-1]

                print("\n==================================================")
                print(f"📊 LIVE SMC SCANNER STATUS ({symbol})")
                print(f"⏰ Scan Time (IST):  {now_ist}")
                print(f"💲 Live Price:       {latest_price:.2f}")
                print(f"🚦 Engine Decision:  {decision} ({reason})")
                print("==================================================")
                print("1️⃣  4H DEALING RANGE & BIAS")
                print(f"   • 4H Swing High:  {h4_sh:.2f}")
                print(f"   • 4H Swing Low:   {h4_sl:.2f}")
                print(f"   • Equilibrium:    {eq_4h:.2f}")
                print(f"   • Overall Bias:   {bias}")
                print("--------------------------------------------------")
                print("2️⃣  1H LIQUIDITY LEVELS")
                print(f"   • Buy-Side Liquidity (BSL):  {h1_bsl:.2f}")
                print(f"   • Sell-Side Liquidity (SSL): {h1_ssl:.2f}")
                print("--------------------------------------------------")
                print("4️⃣  ACTIONABLE EXECUTION PLAN (ENLARGED RANGE)")

                if latest_price > eq_4h:
                    # Bearish Reversal Plan (Premium Zone)
                    planned_entry = h1_bsl
                    planned_sl = h1_bsl + SL_BUFFER
                    planned_tp1 = eq_4h
                    planned_tp2 = h4_sl

                    risk = planned_sl - planned_entry
                    reward_tp1 = planned_entry - planned_tp1
                    reward_tp2 = planned_entry - planned_tp2

                    rr_tp1 = reward_tp1 / risk if risk > 0 else 0
                    rr_tp2 = reward_tp2 / risk if risk > 0 else 0

                    print("   • Direction:       SHORT (Bearish Reversal from Premium)")
                    print(f"   • Trigger:         Sweep 1H BSL ({h1_bsl:.2f}) + 1M Bearish CHoCH")
                    print(f"   • Planned Entry:   {planned_entry:.2f} (1H Buy-Side Liquidity Sweep)")
                    print(f"   • Planned SL:      {planned_sl:.2f} (+${SL_BUFFER:.2f} / 60 Pips Above High)")
                    print(f"   • Target 1 (EQ):   {planned_tp1:.2f} (Equilibrium) -> R:R {rr_tp1:.2f}R")
                    print(f"   • Target 2 (4H SL):{planned_tp2:.2f} (Major 4H Low) -> R:R {rr_tp2:.2f}R")
                else:
                    # Bullish Reversal Plan (Discount Zone)
                    planned_entry = h1_ssl
                    planned_sl = h1_ssl - SL_BUFFER
                    planned_tp1 = eq_4h
                    planned_tp2 = h4_sh

                    risk = planned_entry - planned_sl
                    reward_tp1 = planned_tp1 - planned_entry
                    reward_tp2 = planned_tp2 - planned_entry

                    rr_tp1 = reward_tp1 / risk if risk > 0 else 0
                    rr_tp2 = reward_tp2 / risk if risk > 0 else 0

                    print("   • Direction:       LONG (Bullish Reversal from Discount)")
                    print(f"   • Trigger:         Sweep 1H SSL ({h1_ssl:.2f}) + 1M Bullish CHoCH")
                    print(f"   • Planned Entry:   {planned_entry:.2f} (1H Sell-Side Liquidity Sweep)")
                    print(f"   • Planned SL:      {planned_sl:.2f} (-${SL_BUFFER:.2f} / 60 Pips Below Low)")
                    print(f"   • Target 1 (EQ):   {planned_tp1:.2f} (Equilibrium) -> R:R {rr_tp1:.2f}R")
                    print(f"   • Target 2 (4H SH):{planned_tp2:.2f} (Major 4H High) -> R:R {rr_tp2:.2f}R")

                print("==================================================")

                if decision in ["BUY", "SELL"]:
                    params = result.get("trade_params", {})
                    print("\n🚨 [LIVE TRADE SIGNAL TRIGGERED] 🚨")
                    print(f"   Entry:       {params.get('entry')}")
                    print(f"   Stop Loss:   {params.get('sl')}")
                    print(f"   Take Profit: {params.get('tp')}")
                    print(f"   R:R Ratio:   {params.get('rr')}\n")

            except Exception as e:
                print(f"[{symbol}] Error fetching data: {e}")

        print(f"\nWaiting {SCAN_INTERVAL_SECONDS} seconds for next cycle...")
        time.sleep(SCAN_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_scanner()