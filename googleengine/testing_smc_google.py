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
# Fetch API Key directly from system environment variable (~/.bashrc)
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")

if not TWELVE_DATA_API_KEY:
    print("❌ Error: TWELVE_DATA_API_KEY environment variable is missing.")
    print("Ensure you ran: export TWELVE_DATA_API_KEY='your_api_key'")
    print("Or check that it was added to ~/.bashrc and re-sourced (`source ~/.bashrc`).")
    sys.exit(1)

# Twelve Data Symbol Format
TICKERS = ["XAU/USD", "EUR/USD", "GBP/USD", "BTC/USD"]
SCAN_INTERVAL_SECONDS = 60  # Runs scan once every minute
IST = ZoneInfo("Asia/Kolkata")

# Initialize Twelve Data Client
td = TDClient(apikey=TWELVE_DATA_API_KEY)


def fetch_realtime_data(symbol: str) -> dict:
    """
    Fetches real-time 1M data from Twelve Data (1 API call)
    and resamples locally into 15M, 1H, and 4H DataFrames in IST.
    """
    # Fetch 500 bars of 1-minute data
    ts = td.time_series(symbol=symbol, interval="1min", outputsize=500)
    df_1m = ts.as_pandas()

    if df_1m is None or df_1m.empty:
        raise ValueError(f"No data returned from Twelve Data for '{symbol}'")

    # Sort index chronologically (Twelve Data returns newest first)
    df_1m = df_1m.sort_index()

    # Ensure numeric float types
    for col in ["open", "high", "low", "close"]:
        df_1m[col] = df_1m[col].astype(float)

    # Standardize & Convert Timezone to IST
    if df_1m.index.tz is None:
        df_1m.index = df_1m.index.tz_localize("UTC").tz_convert(IST)
    else:
        df_1m.index = df_1m.index.tz_convert(IST)

    # Resample 1M data into higher timeframes locally
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

    return {"4H": df_4h, "1H": df_1h, "15M": df_15m, "1M": df_1m}


def run_scanner():
    engine = SMCTradingEngine(min_rr=2.0, max_rr=8.0, atr_multiplier=1.0)

    print("==================================================")
    print("   SMC REAL-TIME SCANNER (TWELVE DATA - IST)      ")
    print("==================================================")

    while True:
        now_ist = datetime.now(IST).strftime("%Y-%m-%d %I:%M:%S %p IST")
        print(f"\n--- SCAN CYCLE AT {now_ist} ---")

        for symbol in TICKERS:
            try:
                data = fetch_realtime_data(symbol)
                result = engine.analyze(data)

                decision = result.get("decision", "NO_TRADE")
                reason = result.get("reason", "Setup validated")
                bias = result.get("bias_4h", "N/A")
                latest_price = data["1M"]["close"].iloc[-1]

                if decision in ["BUY", "SELL"]:
                    params = result.get("trade_params", {})
                    print("\n" + "=" * 45)
                    print(f"🚨 [TRADE SIGNAL DETECTED: {symbol}] 🚨")
                    print(f"   Time (IST):    {now_ist}")
                    print(f"   Live Price:    {latest_price:.2f}")
                    print(f"   Decision:      {decision}")
                    print(f"   4H Bias:       {bias}")
                    print(f"   Entry:         {params.get('entry')}")
                    print(f"   Stop Loss:     {params.get('sl')}")
                    print(f"   Take Profit:   {params.get('tp')}")
                    print(f"   R:R Ratio:     {params.get('rr')}")
                    print("=" * 45 + "\n")
                else:
                    print(
                        f"[{symbol:<8}] Price: {latest_price:<8.2f} | Status: {decision:<8} | 4H Bias: {bias:<8} | Reason: {reason}"
                    )

            except Exception as e:
                print(f"[{symbol}] Error fetching data: {e}")

        print(f"\nWaiting {SCAN_INTERVAL_SECONDS} seconds for next bar...")
        time.sleep(SCAN_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_scanner()