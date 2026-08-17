import os
import sys
import time
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo
import pandas as pd
import requests
from twelvedata import TDClient
from googlesmc import SMCTradingEngine

# ==========================================
# CONFIGURATION & ENVIRONMENT SETUP
# ==========================================
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TWELVE_DATA_API_KEY:
    print("❌ Error: TWELVE_DATA_API_KEY environment variable is not set.")
    sys.exit(1)

TICKERS = ["XAU/USD"]
SCAN_INTERVAL_SECONDS = 150  # 2.5 minutes (336 cycles = 672 API credits/day)
IDLE_SLEEP_SECONDS = 300     # Check clock every 5 minutes during Asian session
SL_BUFFER = 6.00             # $6.00 buffer (60 pips) for Gold
IST = ZoneInfo("Asia/Kolkata")

td = TDClient(apikey=TWELVE_DATA_API_KEY)


def send_telegram_alert(message: str):
    """Sends formatted alert message to Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram token/chat_id not set. Skipping Telegram notification.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"⚠️ Failed to send Telegram alert: {e}")


def is_active_session(now_dt: datetime) -> bool:
    """Checks if current time is within London/NY active window (1:30 PM to 3:30 AM IST)."""
    current_time = now_dt.time()
    start_time = dtime(13, 30)  # 1:30 PM IST
    end_time = dtime(3, 30)     # 3:30 AM IST

    if current_time >= start_time or current_time < end_time:
        return True
    return False


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
    last_signal_key = None

    print("==================================================")
    print("  SMC GOLD SCANNER - OPTION B (1:30 PM-3:30 AM IST)")
    print("==================================================")

    send_telegram_alert(
        "🚀 *SMC Gold Scanner Started*\n"
        "Session Window: 1:30 PM to 3:30 AM IST\n"
        "API Mode: Safe Tier (672 Credits/Day)"
    )

    while True:
        now_ist = datetime.now(IST)

        # Check Active Session Window
        if not is_active_session(now_ist):
            print(
                f"[{now_ist.strftime('%I:%M:%S %p IST')}] 😴 Asian Session Idle (Outside 1:30 PM - 3:30 AM IST). Pausing API calls..."
            )
            time.sleep(IDLE_SLEEP_SECONDS)
            continue

        now_str = now_ist.strftime("%Y-%m-%d %I:%M:%S %p IST")

        for symbol in TICKERS:
            try:
                data = fetch_realtime_data(symbol)

                # Higher Timeframe Structure
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
                print(f"⏰ Scan Time (IST):  {now_str}")
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
                    planned_entry = h1_bsl
                    planned_sl = h1_bsl + SL_BUFFER
                    planned_tp1 = eq_4h
                    planned_tp2 = h4_sl
                    risk = planned_sl - planned_entry
                    reward_tp2 = planned_entry - planned_tp2
                    rr_tp2 = reward_tp2 / risk if risk > 0 else 0

                    print("   • Direction:       SHORT (Bearish Reversal from Premium)")
                    print(f"   • Trigger:         Sweep 1H BSL ({h1_bsl:.2f}) + 1M Bearish CHoCH")
                    print(f"   • Planned Entry:   {planned_entry:.2f} (1H Buy-Side Liquidity Sweep)")
                    print(f"   • Planned SL:      {planned_sl:.2f} (+${SL_BUFFER:.2f} / 60 Pips Above High)")
                    print(f"   • Target 1 (EQ):   {planned_tp1:.2f} (Equilibrium)")
                    print(f"   • Target 2 (4H SL):{planned_tp2:.2f} (Major 4H Low) -> R:R {rr_tp2:.2f}R")
                else:
                    planned_entry = h1_ssl
                    planned_sl = h1_ssl - SL_BUFFER
                    planned_tp1 = eq_4h
                    planned_tp2 = h4_sh
                    risk = planned_entry - planned_sl
                    reward_tp2 = planned_tp2 - planned_entry
                    rr_tp2 = reward_tp2 / risk if risk > 0 else 0

                    print("   • Direction:       LONG (Bullish Reversal from Discount)")
                    print(f"   • Trigger:         Sweep 1H SSL ({h1_ssl:.2f}) + 1M Bullish CHoCH")
                    print(f"   • Planned Entry:   {planned_entry:.2f} (1H Sell-Side Liquidity Sweep)")
                    print(f"   • Planned SL:      {planned_sl:.2f} (-${SL_BUFFER:.2f} / 60 Pips Below Low)")
                    print(f"   • Target 1 (EQ):   {planned_tp1:.2f} (Equilibrium)")
                    print(f"   • Target 2 (4H SH):{planned_tp2:.2f} (Major 4H High) -> R:R {rr_tp2:.2f}R")

                print("==================================================")

                # Telegram Alert Dispatch Logic
                if decision in ["BUY", "SELL"]:
                    current_signal_key = (
                        f"{decision}_{latest_price:.1f}_{now_ist.strftime('%H%M')}"
                    )

                    if current_signal_key != last_signal_key:
                        last_signal_key = current_signal_key
                        params = result.get("trade_params", {})

                        msg = (
                            f"🚨 *SMC TRADE SIGNAL: {symbol}*\n\n"
                            f"• *Decision:* `{decision}`\n"
                            f"• *Entry:* `{params.get('entry', latest_price)}`\n"
                            f"• *Stop Loss:* `{params.get('sl', planned_sl):.2f}`\n"
                            f"• *Target 1 (EQ):* `{planned_tp1:.2f}`\n"
                            f"• *Target 2 (4H):* `{planned_tp2:.2f}`\n"
                            f"• *4H Bias:* `{bias}`\n"
                            f"• *Time (IST):* `{now_str}`"
                        )
                        send_telegram_alert(msg)

            except Exception as e:
                print(f"[{symbol}] Error fetching data: {e}")

        time.sleep(SCAN_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_scanner()