from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import yfinance as yf

IST = ZoneInfo("Asia/Kolkata")


def inspect_market_state(ticker="GC=F"):
    df_1m = yf.download(ticker, period="5d", interval="1m", progress=False)

    if df_1m.empty:
        print(f"Error: Unable to fetch data for {ticker}")
        return

    if isinstance(df_1m.columns, pd.MultiIndex):
        df_1m.columns = df_1m.columns.get_level_values(0)

    df_1m = df_1m.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
        }
    )

    # Convert timestamps to IST
    if df_1m.index.tz is None:
        df_1m.index = df_1m.index.tz_localize("UTC").tz_convert(IST)
    else:
        df_1m.index = df_1m.index.tz_convert(IST)

    # Resample Timeframes
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

    # 1. 4H Structure & Bias
    h4_high = df_4h["high"].tail(20).max()
    h4_low = df_4h["low"].tail(20).min()
    equilibrium = (h4_high + h4_low) / 2
    bias = (
        "BEARISH (Premium Zone)"
        if current_price > equilibrium
        else "BULLISH (Discount Zone)"
    )

    # 2. 1H Liquidity Pools
    h1_bsl = df_1h["high"].iloc[-10:-1].max()  # Buy-side liquidity (Highs)
    h1_ssl = df_1h["low"].iloc[-10:-1].min()  # Sell-side liquidity (Lows)

    swept_bsl = current_price >= h1_bsl or df_1h["high"].iloc[-1] >= h1_bsl
    swept_ssl = current_price <= h1_ssl or df_1h["low"].iloc[-1] <= h1_ssl

    # 3. 15M FVG Detection
    fvg_type = "None"
    fvg_range = "N/A"

    for i in range(len(df_15m) - 1, max(2, len(df_15m) - 10), -1):
        if df_15m["low"].iloc[i] > df_15m["high"].iloc[i - 2]:
            fvg_type = "Bullish FVG"
            fvg_range = f"{df_15m['high'].iloc[i-2]:.2f} - {df_15m['low'].iloc[i]:.2f}"
            break
        elif df_15m["high"].iloc[i] < df_15m["low"].iloc[i - 2]:
            fvg_type = "Bearish FVG"
            fvg_range = f"{df_15m['low'].iloc[i]:.2f} - {df_15m['high'].iloc[i-2]:.2f}"
            break

    # 4. Print Summary Report
    print("==================================================")
    print(f"📊 LIVE SMC MARKET VERIFICATION ({ticker})")
    print(f"⏰ Bar Time (IST):   {last_time_ist}")
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
    print(f"   • BSL Swept?                 {'YES' if swept_bsl else 'NO'}")
    print(f"   • SSL Swept?                 {'YES' if swept_ssl else 'NO'}")
    print("--------------------------------------------------")
    print("3️⃣  15M POI (FAIR VALUE GAP / OB)")
    print(f"   • Active FVG Type: {fvg_type}")
    print(f"   • FVG Price Zone:  {fvg_range}")
    print("--------------------------------------------------")
    print("4️⃣  ACTIONABLE EXECUTION PLAN")
    if current_price > equilibrium:
        print(
            f"   • PLAN: IF price spikes above 1H High ({h1_bsl:.2f}) and rejects,"
        )
        print(
            f"           THEN watch for 15M Bearish CHoCH to SELL down to {equilibrium:.2f}."
        )
    else:
        print(
            f"   • PLAN: IF price drops below 1H Low ({h1_ssl:.2f}) and recovers,"
        )
        print(
            f"           THEN watch for 15M Bullish CHoCH to BUY up to {equilibrium:.2f}."
        )
    print("==================================================\n")


if __name__ == "__main__":
    inspect_market_state("GC=F")