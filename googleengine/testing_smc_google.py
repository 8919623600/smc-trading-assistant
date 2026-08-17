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

# Single Target Asset
TICKERS = ["XAU/USD"]
SCAN_INTERVAL_SECONDS = 60  # Scan every 60 seconds
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
    """
    Fetches real-time multi-timeframe data via Twelve Data in UTC and converts to IST.
    Uses 15M candles for accurate higher timeframe resamples (1H, 4H) and 1M for entries.
    """
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
        print(f"\n--- SCAN CYCLE AT {now_ist} ---")

        for symbol in TICKERS:
            try:
                data = fetch_realtime_data(symbol)

                h4_sh, h4_sl = find_smc_swings(data["4H"], window=2)
                eq_4h = (h4_sh + h4_sl) / 2

                result = engine.analyze(data)

                decision = result.get("decision", "NO_TRADE")
                reason = result.get("reason", "Setup validated")
                bias = result.get("bias_4h", "N/A")
                latest_price = data["1M"]["close"].iloc[-1]

                if decision in ["BUY", "SELL"]:
                    params = result.get("trade_params", {})
                    print("\n" + "=" * 45)
                    print(f"🚨 [GOLD TRADE SIGNAL DETECTED: {symbol}] 🚨")
                    print(f"   Time (IST):        {now_ist}")
                    print(f"   Live Price:        {latest_price:.2f}")
                    print(f"   Decision:          {decision}")
                    print(f"   4H Bias:           {bias}")
                    print(f"   4H Swing Range:    {h4_sl:.2f} - {h4_sh:.2f} (EQ: {eq_4h:.2f})")
                    print(f"   Entry:             {params.get('entry')}")
                    print(f"   Stop Loss:         {params.get('sl')}")
                    print(f"   Take Profit:       {params.get('tp')}")
                    print(f"   R:R Ratio:         {params.get('rr')}")
                    print("=" * 45 + "\n")
                else:
                    print(
                        f"[{symbol:<8}] Price: {latest_price:<8.2f} | Status: {decision:<8} | 4H Bias: {bias:<8} | EQ: {eq_4h:<8.2f} | Reason: {reason}"
                    )

            except Exception as e:
                print(f"[{symbol}] Error fetching data: {e}")

        print(f"\nWaiting {SCAN_INTERVAL_SECONDS} seconds for next cycle...")
        time.sleep(SCAN_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_scanner()