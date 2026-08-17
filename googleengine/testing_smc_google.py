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
# CONFIGURATION & ACCOUNT SETTINGS
# ==========================================
NEWS_PAUSE = False                      # Set to True to halt scanning during high-impact news

# Account & Risk Parameters for Lot Sizing (Adjust to your actual broker specs)
ACCOUNT_BALANCE = 10000.0               # Your account balance in USD
RISK_PERCENTAGE = 1.0                   # Max risk per trade (% of account, e.g. 1.0%)
CONTRACT_SIZE_GOLD = 100                # Standard Gold contract size (1 lot = 100 oz)
MIN_REQUIRED_RR = 2.0                   # Minimum acceptable Reward-to-Risk ratio for Target 2

TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TWELVE_DATA_API_KEY:
    print("❌ Error: TWELVE_DATA_API_KEY environment variable is not set.")
    sys.exit(1)

TICKERS = ["XAU/USD"]
SCAN_INTERVAL_SECONDS = 150  # 2.5 minutes
IDLE_SLEEP_SECONDS = 300     # 5 minutes
IST = ZoneInfo("Asia/Kolkata")
TRADE_HISTORY_FILE = "trade_history.csv"

td = TDClient(apikey=TWELVE_DATA_API_KEY)


def send_telegram_alert(message: str):
    """Sends formatted alert message to Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"⚠️ Telegram alert failed: {e}")


def is_active_session(now_dt: datetime) -> bool:
    """Checks if current time is within London/NY active window (1:30 PM to 3:30 AM IST)."""
    current_time = now_dt.time()
    return current_time >= dtime(13, 30) or current_time < dtime(3, 30)


def initialize_trade_history():
    """Initializes the CSV file for tracking trade outcomes."""
    if not os.path.exists(TRADE_HISTORY_FILE):
        pd.DataFrame(columns=[
            "trade_id", "timestamp", "symbol", "decision", "entry", "sl", "tp1", "tp2", "lots", "status", "exit_time"
        ]).to_csv(TRADE_HISTORY_FILE, index=False)


def log_new_trade(trade_id, timestamp, symbol, decision, entry, sl, tp1, tp2, lots):
    """Logs a newly triggered trade into trade_history.csv."""
    initialize_trade_history()
    df = pd.read_csv(TRADE_HISTORY_FILE)
    new_row = {
        "trade_id": trade_id, "timestamp": timestamp, "symbol": symbol, "decision": decision,
        "entry": entry, "sl": sl, "tp1": tp1, "tp2": tp2, "lots": lots, "status": "PENDING", "exit_time": "N/A"
    }
    pd.concat([df, pd.DataFrame([new_row])], ignore_index=True).to_csv(TRADE_HISTORY_FILE, index=False)


def evaluate_pending_trades(current_high: float, current_low: float, now_str: str):
    """Checks active pending trades against current price action to see if SL or TP2 was hit."""
    if not os.path.exists(TRADE_HISTORY_FILE):
        return
    df = pd.read_csv(TRADE_HISTORY_FILE)
    updated = False
    for idx, row in df.iterrows():
        if row["status"] == "PENDING":
            decision, sl, tp2, trade_id = row["decision"], float(row["sl"]), float(row["tp2"]), row["trade_id"]
            if (decision == "BUY" and current_low <= sl) or (decision == "SELL" and current_high >= sl):
                df.at[idx, "status"] = "LOSS"
                df.at[idx, "exit_time"] = now_str
                updated = True
                send_telegram_alert(f"❌ *TRADE STOPPED OUT (LOSS)*\nID: `{trade_id}`\nHit structural SL at `{sl:.2f}`")
            elif (decision == "BUY" and current_high >= tp2) or (decision == "SELL" and current_low <= tp2):
                df.at[idx, "status"] = "WIN_TP2"
                df.at[idx, "exit_time"] = now_str
                updated = True
                send_telegram_alert(f"🎯 *TRADE TARGET REACHED (WIN)*\nID: `{trade_id}`\nHit TP2 at `{tp2:.2f}`")
    if updated:
        df.to_csv(TRADE_HISTORY_FILE, index=False)


def find_smc_swings(df: pd.DataFrame, window: int = 2):
    """Identifies verified SMC Fractal Swing Highs and Swing Lows."""
    swing_highs = [
        df["high"].iloc[i] for i in range(window, len(df) - window)
        if all(df["high"].iloc[i] > df["high"].iloc[i - j] for j in range(1, window + 1)) and
           all(df["high"].iloc[i] >= df["high"].iloc[i + j] for j in range(1, window + 1))
    ]
    swing_lows = [
        df["low"].iloc[i] for i in range(window, len(df) - window)
        if all(df["low"].iloc[i] < df["low"].iloc[i - j] for j in range(1, window + 1)) and
           all(df["low"].iloc[i] <= df["low"].iloc[i + j] for j in range(1, window + 1))
    ]
    active_sh = swing_highs[-1] if swing_highs else df["high"].max()
    active_sl = swing_lows[-1] if swing_lows else df["low"].min()
    return active_sh, active_sl


def calculate_atr(df: pd.DataFrame, period: int = 14) -> float:
    """Calculates Average True Range for dynamic structural noise buffer."""
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    return float(true_range.rolling(period).mean().iloc[-1])


def fetch_realtime_data(symbol: str) -> dict:
    """Fetches real-time multi-timeframe data via Twelve Data in UTC and converts to IST."""
    ts_15m = td.time_series(symbol=symbol, interval="15min", outputsize=500, timezone="UTC").as_pandas()
    ts_1m = td.time_series(symbol=symbol, interval="1min", outputsize=100, timezone="UTC").as_pandas()

    if ts_15m is None or ts_1m is None or ts_15m.empty or ts_1m.empty:
        raise ValueError(f"No data returned from Twelve Data for '{symbol}'")

    for df in [ts_15m, ts_1m]:
        df.index = pd.to_datetime(df.index)
        df.sort_index(inplace=True)
        for col in ["open", "high", "low", "close"]:
            df[col] = df[col].astype(float)

        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC").tz_convert(IST)
        else:
            df.index = df.index.tz_convert(IST)

    df_1h = ts_15m.resample("1h").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    df_4h = ts_15m.resample("4h").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()

    return {"4H": df_4h, "1H": df_1h, "15M": ts_15m, "1M": ts_1m}


def run_scanner():
    engine = SMCTradingEngine(min_rr=2.0, max_rr=8.0, atr_multiplier=1.0)
    initialize_trade_history()
    last_signal_key = None

    print("==================================================")
    print("  SMC GOLD SCANNER + LOGICAL SL & R:R FILTER     ")
    print("==================================================")

    while True:
        now_ist = datetime.now(IST)

        if NEWS_PAUSE:
            print(f"[{now_ist.strftime('%I:%M:%S %p IST')}] 🛑 NEWS PAUSE ACTIVE. Idling...")
            time.sleep(IDLE_SLEEP_SECONDS)
            continue

        if not is_active_session(now_ist):
            print(f"[{now_ist.strftime('%I:%M:%S %p IST')}] 😴 Session Closed. Idling...")
            time.sleep(IDLE_SLEEP_SECONDS)
            continue

        now_str = now_ist.strftime("%Y-%m-%d %I:%M:%S %p IST")

        for symbol in TICKERS:
            try:
                data = fetch_realtime_data(symbol)
                evaluate_pending_trades(data["1M"]["high"].iloc[-1], data["1M"]["low"].iloc[-1], now_str)

                h4_sh, h4_sl = find_smc_swings(data["4H"], window=2)
                eq_4h = (h4_sh + h4_sl) / 2
                h1_bsl, h1_ssl = find_smc_swings(data["1H"], window=2)
                atr_val = calculate_atr(data["1H"], period=14)

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
                print(f"   • 1H ATR (Noise): {atr_val:.2f}")
                print("--------------------------------------------------")
                print("2️⃣  LOGICAL EXECUTION & RISK PLAN")

                if latest_price > eq_4h:
                    # SHORT SETUP
                    planned_entry = h1_bsl
                    structural_ceiling = max(h4_sh, h1_bsl)
                    planned_sl = structural_ceiling + (atr_val * 0.5)
                    planned_tp1 = eq_4h
                    planned_tp2 = h4_sl
                    risk_points = planned_sl - planned_entry
                    reward_tp2 = planned_entry - planned_tp2
                    rr_tp2 = reward_tp2 / risk_points if risk_points > 0 else 0

                    print("   • Direction:       SHORT (Bearish Reversal from Premium)")
                    print(f"   • Planned Entry:   {planned_entry:.2f} (1H BSL Sweep)")
                    print(f"   • Logical SL:      {planned_sl:.2f} (Structural High + 0.5*ATR)")
                    print(f"   • Target 1 (EQ):   {planned_tp1:.2f}")
                    print(f"   • Target 2 (4H SL):{planned_tp2:.2f} -> R:R {rr_tp2:.2f}R")
                else:
                    # LONG SETUP
                    planned_entry = h1_ssl
                    structural_floor = min(h4_sl, h1_ssl)
                    planned_sl = structural_floor - (atr_val * 0.5)
                    planned_tp1 = eq_4h
                    planned_tp2 = h4_sh
                    risk_points = planned_entry - planned_sl
                    reward_tp2 = planned_tp2 - planned_entry
                    rr_tp2 = reward_tp2 / risk_points if risk_points > 0 else 0

                    print("   • Direction:       LONG (Bullish Reversal from Discount)")
                    print(f"   • Planned Entry:   {planned_entry:.2f} (1H SSL Sweep)")
                    print(f"   • Logical SL:      {planned_sl:.2f} (Structural Low - 0.5*ATR)")
                    print(f"   • Target 1 (EQ):   {planned_tp1:.2f}")
                    print(f"   • Target 2 (4H SH):{planned_tp2:.2f} -> R:R {rr_tp2:.2f}R")

                # STRICT R:R FILTER CHECK
                if rr_tp2 < MIN_REQUIRED_RR:
                    print(f"   ❌ REJECTED: R:R ({rr_tp2:.2f}R) is below minimum required {MIN_REQUIRED_RR}R.")
                    decision = "WAIT"
                else:
                    print(f"   ✔ APPROVED: High-asymmetry setup verified.")

                # Lot Sizing Calculation based on % Risk
                dollar_risk_allowed = ACCOUNT_BALANCE * (RISK_PERCENTAGE / 100.0)
                risk_per_lot = risk_points * CONTRACT_SIZE_GOLD
                recommended_lots = round(dollar_risk_allowed / risk_per_lot, 2) if risk_per_lot > 0 else 0.01
                recommended_lots = max(0.01, recommended_lots)

                print(f"   • Position Sizing: {recommended_lots} Lots (Risking ${dollar_risk_allowed:.2f} / {RISK_PERCENTAGE}%)")
                print("==================================================")

                if decision in ["BUY", "SELL"]:
                    current_signal_key = f"{decision}_{latest_price:.1f}_{now_ist.strftime('%H%M')}"
                    if current_signal_key != last_signal_key:
                        last_signal_key = current_signal_key
                        trade_id = f"XAU_{now_ist.strftime('%Y%m%d_%H%M')}"
                        log_new_trade(trade_id, now_str, symbol, decision, planned_entry, planned_sl, planned_tp1, planned_tp2, recommended_lots)

                        msg = (
                            f"🚨 *SMC STRUCTURAL TRADE SIGNAL ({trade_id})*\n\n"
                            f"• *Decision:* `{decision}`\n"
                            f"• *Entry:* `{planned_entry:.2f}`\n"
                            f"• *Logical SL:* `{planned_sl:.2f}`\n"
                            f"• *Target 1 (EQ):* `{planned_tp1:.2f}`\n"
                            f"• *Target 2 (4H):* `{planned_tp2:.2f}`\n"
                            f"• *Recommended Lots:* `{recommended_lots}`\n"
                            f"• *Risk R:R:* `{rr_tp2:.2f}R`\n"
                            f"• *Time (IST):* `{now_str}`"
                        )
                        send_telegram_alert(msg)

            except Exception as e:
                print(f"[{symbol}] Error fetching data: {e}")

        time.sleep(SCAN_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_scanner()