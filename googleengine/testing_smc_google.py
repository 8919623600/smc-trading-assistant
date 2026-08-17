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
# MANUAL CIRCUIT BREAKER: Set to True to halt all trading/API calls during high-impact news.
NEWS_PAUSE = False 

TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TWELVE_DATA_API_KEY:
    print("❌ Error: TWELVE_DATA_API_KEY environment variable is not set.")
    sys.exit(1)

TICKERS = ["XAU/USD"]
SCAN_INTERVAL_SECONDS = 150  # 2.5 minutes
IDLE_SLEEP_SECONDS = 300     # 5 minutes
SL_BUFFER = 6.00             # $6.00 (60 pips) for Gold
IST = ZoneInfo("Asia/Kolkata")
TRADE_HISTORY_FILE = "trade_history.csv"

td = TDClient(apikey=TWELVE_DATA_API_KEY)

def send_telegram_alert(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload, timeout=5)
    except Exception as e: print(f"⚠️ Telegram alert failed: {e}")

def is_active_session(now_dt: datetime) -> bool:
    current_time = now_dt.time()
    return (current_time >= dtime(13, 30) or current_time < dtime(3, 30))

def initialize_trade_history():
    if not os.path.exists(TRADE_HISTORY_FILE):
        pd.DataFrame(columns=["trade_id", "timestamp", "symbol", "decision", "entry", "sl", "tp1", "tp2", "status", "exit_time"]).to_csv(TRADE_HISTORY_FILE, index=False)

def log_new_trade(trade_id, timestamp, symbol, decision, entry, sl, tp1, tp2):
    initialize_trade_history()
    df = pd.read_csv(TRADE_HISTORY_FILE)
    new_row = {"trade_id": trade_id, "timestamp": timestamp, "symbol": symbol, "decision": decision, "entry": entry, "sl": sl, "tp1": tp1, "tp2": tp2, "status": "PENDING", "exit_time": "N/A"}
    pd.concat([df, pd.DataFrame([new_row])], ignore_index=True).to_csv(TRADE_HISTORY_FILE, index=False)

def evaluate_pending_trades(current_high: float, current_low: float, now_str: str):
    if not os.path.exists(TRADE_HISTORY_FILE): return
    df = pd.read_csv(TRADE_HISTORY_FILE)
    updated = False
    for idx, row in df.iterrows():
        if row["status"] == "PENDING":
            decision, sl, tp2, trade_id = row["decision"], float(row["sl"]), float(row["tp2"]), row["trade_id"]
            if (decision == "BUY" and current_low <= sl) or (decision == "SELL" and current_high >= sl):
                df.at[idx, "status"] = "LOSS"
                df.at[idx, "exit_time"] = now_str
                updated = True
                send_telegram_alert(f"❌ *TRADE STOPPED OUT (LOSS)*\nID: `{trade_id}`\nHit SL at `{sl:.2f}`")
            elif (decision == "BUY" and current_high >= tp2) or (decision == "SELL" and current_low <= tp2):
                df.at[idx, "status"] = "WIN_TP2"
                df.at[idx, "exit_time"] = now_str
                updated = True
                send_telegram_alert(f"🎯 *TRADE TARGET REACHED (WIN)*\nID: `{trade_id}`\nHit TP2 at `{tp2:.2f}`")
    if updated: df.to_csv(TRADE_HISTORY_FILE, index=False)

def print_monthly_report():
    if not os.path.exists(TRADE_HISTORY_FILE): return
    df = pd.read_csv(TRADE_HISTORY_FILE)
    if df.empty: return
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["Month"] = df["timestamp"].dt.to_period("M")
    print("\n📊 MONTHLY PERFORMANCE REPORT")
    for month, group in df.groupby("Month"):
        total = len(group[group["status"] != "PENDING"])
        wins = len(group[group["status"].str.contains("WIN", na=False)])
        losses = len(group[group["status"] == "LOSS"])
        print(f"🗓️ {month} | Trades: {total} | Win: {wins} | Loss: {losses} | Win Rate: {(wins/total*100 if total>0 else 0):.1f}%")

def find_smc_swings(df: pd.DataFrame, window: int = 2):
    swing_highs = [df["high"].iloc[i] for i in range(window, len(df)-window) if all(df["high"].iloc[i] > df["high"].iloc[i-j] for j in range(1, window+1)) and all(df["high"].iloc[i] >= df["high"].iloc[i+j] for j in range(1, window+1))]
    swing_lows = [df["low"].iloc[i] for i in range(window, len(df)-window) if all(df["low"].iloc[i] < df["low"].iloc[i-j] for j in range(1, window+1)) and all(df["low"].iloc[i] <= df["low"].iloc[i+j] for j in range(1, window+1))]
    active_sh = swing_highs[-1] if swing_highs else df["high"].max()
    active_sl = swing_lows[-1] if swing_lows else df["low"].min()
    return active_sh, active_sl

def fetch_realtime_data(symbol: str) -> dict:
    ts_15m = td.time_series(symbol=symbol, interval="15min", outputsize=500, timezone="UTC").as_pandas()
    ts_1m = td.time_series(symbol=symbol, interval="1min", outputsize=100, timezone="UTC").as_pandas()
    for df in [ts_15m, ts_1m]:
        df.index = pd.to_datetime(df.index).tz_convert(IST)
        for col in ["open", "high", "low", "close"]: df[col] = df[col].astype(float)
    return {"4H": ts_15m.resample("4h").agg({"open":"first", "high":"max", "low":"min", "close":"last"}), 
            "1H": ts_15m.resample("1h").agg({"open":"first", "high":"max", "low":"min", "close":"last"}), 
            "1M": ts_1m}

def run_scanner():
    engine = SMCTradingEngine(min_rr=2.0, max_rr=8.0, atr_multiplier=1.0)
    initialize_trade_history()
    print("🚀 SMC GOLD SCANNER ACTIVE")

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

        try:
            data = fetch_realtime_data("XAU/USD")
            evaluate_pending_trades(data["1M"]["high"].iloc[-1], data["1M"]["low"].iloc[-1], now_ist.strftime("%Y-%m-%d %H:%M:%S"))
            
            result = engine.analyze(data)
            decision = result.get("decision", "NO_TRADE")
            if decision in ["BUY", "SELL"]:
                h4_sh, h4_sl = find_smc_swings(data["4H"])
                h1_bsl, h1_ssl = find_smc_swings(data["1H"])
                planned_entry = h1_bsl if decision == "SELL" else h1_ssl
                msg = f"🚨 *SMC SIGNAL:* `{decision}` | *Entry:* `{planned_entry:.2f}`"
                send_telegram_alert(msg)
                log_new_trade(f"XAU_{now_ist.strftime('%Y%m%d_%H%M')}", now_ist.strftime('%Y-%m-%d %H:%M:%S'), "XAU/USD", decision, planned_entry, planned_entry+(SL_BUFFER if decision=="SELL" else -SL_BUFFER), (h4_sh+h4_sl)/2, h4_sl if decision=="SELL" else h4_sh)
            
            print(f"[{now_ist.strftime('%I:%M:%S %p IST')}] Scan complete. Decision: {decision}")
        except Exception as e: print(f"Error: {e}")
        time.sleep(SCAN_INTERVAL_SECONDS)

if __name__ == "__main__":
    run_scanner()