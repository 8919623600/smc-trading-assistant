from datetime import datetime
import time
import pandas as pd
import yfinance as yf
from googlesmc import SMCTradingEngine

# ==========================================
# CONFIGURATION
# ==========================================
TICKERS = ["GC=F", "EURUSD=X", "GBPUSD=X", "BTC-USD"]  # Symbols to monitor
SCAN_INTERVAL_SECONDS = 60  # Check frequency (in seconds)


def fetch_real_data(ticker: str) -> dict:
    """Downloads 1M data from Yahoo Finance and resamples it into 15M, 1H, and 4H timeframes."""
    df_1m = yf.download(ticker, period="5d", interval="1m", progress=False)

    if df_1m.empty:
        raise ValueError(f"No data returned for ticker '{ticker}'")

    # Clean MultiIndex columns if present
    if isinstance(df_1m.columns, pd.MultiIndex):
        df_1m.columns = df_1m.columns.get_level_values(0)

    # Standardize column names
    df_1m = df_1m.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    )

    df_1m.index = pd.to_datetime(df_1m.index)

    # Resample 1M data into higher timeframes
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
    """Runs a continuous live loop scanning all configured tickers."""
    engine = SMCTradingEngine(min_rr=2.0, max_rr=8.0, atr_multiplier=1.0)

    print("==================================================")
    print("      SMC MULTI-ASSET REAL-TIME SCANNER STARTED   ")
    print("==================================================")

    while True:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n--- SCAN CYCLE AT {timestamp} ---")

        for ticker in TICKERS:
            try:
                data = fetch_real_data(ticker)
                result = engine.analyze(data)

                decision = result.get("decision", "NO_TRADE")
                reason = result.get("reason", "Setup validated")
                bias = result.get("bias_4h", "N/A")

                # Trigger Signal Alert
                if decision in ["BUY", "SELL"]:
                    params = result.get("trade_params", {})
                    print("\n" + "=" * 40)
                    print(f"🚨 [TRADE SIGNAL DETECTED: {ticker}] 🚨")
                    print(f"   Decision: {decision}")
                    print(f"   4H Bias:  {bias}")
                    print(f"   Entry:    {params.get('entry')}")
                    print(f"   StopLoss: {params.get('sl')}")
                    print(f"   TakeProf: {params.get('tp')}")
                    print(f"   RR Ratio: {params.get('rr')}")
                    print("=" * 40 + "\n")
                else:
                    print(
                        f"[{ticker:<8}] Status: {decision:<8} | 4H Bias: {bias:<8} | Reason: {reason}"
                    )

            except Exception as e:
                print(f"[{ticker}] Error during scan: {e}")

        print(f"\nSleeping for {SCAN_INTERVAL_SECONDS} seconds...")
        time.sleep(SCAN_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_scanner()