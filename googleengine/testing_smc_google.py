import os
import sys
import time
import math
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo
import pandas as pd
import requests
from twelvedata import TDClient
from googlesmc import SMCTradingEngine

# ==========================================
# CONFIGURATION & ACCOUNT SETTINGS
# ==========================================
NEWS_PAUSE = False
MAX_DOLLAR_RISK = 10.0
MIN_REQUIRED_RR = 2.0
MAX_DAILY_LOSSES = 2

ASSET_CONFIG = {
    "XAU/USD": {"contract_size": 100, "quote_usd": True, "name": "Gold"},
    "EUR/USD": {"contract_size": 100000, "quote_usd": True, "name": "Euro / US Dollar"}
}

TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TWELVE_DATA_API_KEY:
    print("❌ Error: TWELVE_DATA_API_KEY environment variable is not set.")
    sys.exit(1)

TICKERS = ["XAU/USD", "EUR/USD"]
SCAN_INTERVAL_SECONDS = 180
API_THROTTLE_SECONDS = 15
IDLE_SLEEP_SECONDS = 300
IST = ZoneInfo("Asia/Kolkata")
TRADE_HISTORY_FILE = "trade_history.csv"
MISTAKE_JOURNAL_FILE = "mistake_journal.csv"
LOG_FILE = "scanner.log"

td = TDClient(apikey=TWELVE_DATA_API_KEY)


def manage_log_size():
    if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 5 * 1024 * 1024:
        with open(LOG_FILE, "w") as f:
            f.write(f"[{datetime.now(IST):%Y-%m-%d %H:%M:%S}] Log rotated due to size limit.\n")


def send_telegram_alert(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"},
            timeout=5
        )
    except Exception as e:
        print(f"⚠️ Telegram alert failed: {e}")


def is_active_session(now_dt: datetime) -> bool:
    t = now_dt.time()
    return t >= dtime(13, 30) or t < dtime(3, 30)


def initialize_trade_history():
    if not os.path.exists(TRADE_HISTORY_FILE):
        pd.DataFrame(columns=[
            "trade_id", "timestamp", "symbol", "decision", "entry", "sl", "tp1", "tp2", "lots", "status", "exit_time", "be_active"
        ]).to_csv(TRADE_HISTORY_FILE, index=False)
    else:
        df = pd.read_csv(TRADE_HISTORY_FILE)
        closed = df[df["status"] != "PENDING"]
        if not closed.empty:
            wins = len(closed[closed["status"] == "WIN"])
            total = len(closed)
            print(f"📈 [PERFORMANCE] Closed: {total} | Wins: {wins} | Win Rate: {(wins / total) * 100:.1f}%")


def check_daily_circuit_breaker() -> bool:
    if not os.path.exists(TRADE_HISTORY_FILE):
        return False
    df = pd.read_csv(TRADE_HISTORY_FILE)
    if "exit_time" not in df.columns or "status" not in df.columns:
        return False
    today_str = datetime.now(IST).strftime("%Y-%m-%d")
    losses = df[(df["status"] == "LOSS") & (df["exit_time"].str.startswith(today_str, na=False))]
    if len(losses) >= MAX_DAILY_LOSSES:
        print(f"🔴 [CIRCUIT BREAKER] {len(losses)} losses today. Halting execution.")
        return True
    return False


def log_trade_mistake(trade_id, symbol, decision, entry, sl, exit_price, atr_val, now_str):
    row = pd.DataFrame([{
        "trade_id": trade_id, "timestamp": now_str, "symbol": symbol, "decision": decision,
        "entry_price": entry, "stop_loss": sl, "exit_price": exit_price,
        "atr_at_entry": atr_val, "points_lost": round(abs(exit_price - entry), 5)
    }])
    row.to_csv(MISTAKE_JOURNAL_FILE, mode='a', header=not os.path.exists(MISTAKE_JOURNAL_FILE), index=False)
    print(f"📝 [MISTAKE JOURNAL] Logged autopsy for trade ID: {trade_id}")


def evaluate_pending_trades(high: float, low: float, atr_val: float, now_str: str):
    if not os.path.exists(TRADE_HISTORY_FILE):
        return
    df = pd.read_csv(TRADE_HISTORY_FILE)
    updated = False

    for idx, row in df[df["status"] == "PENDING"].iterrows():
        dec, entry, sl, tp1, tp2 = row["decision"], float(row["entry"]), float(row["sl"]), float(row["tp1"]), float(row["tp2"])
        tid, sym, be_active = row["trade_id"], row["symbol"], int(row.get("be_active", 0))

        if dec == "BUY":
            if high >= tp1 and not be_active:
                df.loc[idx, ["sl", "be_active"]] = [entry, 1]
                updated = True
                send_telegram_alert(f"🛡️ *Breakeven Activated* for **{sym}** BUY (`{tid}`).")
            if low <= float(df.loc[idx, "sl"]):
                df.loc[idx, ["status", "exit_time"]] = ["LOSS", now_str]
                updated = True
                send_telegram_alert(f"❌ *STOPPED OUT (LOSS)* [{sym}] ID: `{tid}`")
                log_trade_mistake(tid, sym, dec, entry, sl, low, atr_val, now_str)
            elif high >= tp2:
                df.loc[idx, ["status", "exit_time"]] = ["WIN", now_str]
                updated = True
                send_telegram_alert(f"🎯 *TARGET REACHED (WIN)* [{sym}] ID: `{tid}`")

        elif dec == "SELL":
            if low <= tp1 and not be_active:
                df.loc[idx, ["sl", "be_active"]] = [entry, 1]
                updated = True
                send_telegram_alert(f"🛡️ *Breakeven Activated* for **{sym}** SELL (`{tid}`).")
            if high >= float(df.loc[idx, "sl"]):
                df.loc[idx, ["status", "exit_time"]] = ["LOSS", now_str]
                updated = True
                send_telegram_alert(f"❌ *STOPPED OUT (LOSS)* [{sym}] ID: `{tid}`")
                log_trade_mistake(tid, sym, dec, entry, sl, high, atr_val, now_str)
            elif low <= tp2:
                df.loc[idx, ["status", "exit_time"]] = ["WIN", now_str]
                updated = True
                send_telegram_alert(f"🎯 *TARGET REACHED (WIN)* [{sym}] ID: `{tid}`")

    if updated:
        df.to_csv(TRADE_HISTORY_FILE, index=False)


def calculate_atr(df: pd.DataFrame, period: int = 14) -> float:
    tr = pd.concat([df['high'] - df['low'], (df['high'] - df['close'].shift()).abs(), (df['low'] - df['close'].shift()).abs()], axis=1).max(axis=1)
    return float(tr.rolling(period).mean().iloc[-1])


def fetch_realtime_data(symbol: str) -> dict:
    ts_15m = td.time_series(symbol=symbol, interval="15min", outputsize=500, timezone="UTC").as_pandas()
    ts_1m = td.time_series(symbol=symbol, interval="1min", outputsize=100, timezone="UTC").as_pandas()

    if ts_15m is None or ts_1m is None or ts_15m.empty or ts_1m.empty:
        raise ValueError(f"No data returned for '{symbol}'")

    for df in [ts_15m, ts_1m]:
        df.index = pd.to_datetime(df.index)
        df.sort_index(inplace=True)
        df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].astype(float)
        df.index = df.index.tz_localize("UTC").tz_convert(IST) if df.index.tz is None else df.index.tz_convert(IST)

    return {
        "4H": ts_15m.resample("4h").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna(),
        "1H": ts_15m.resample("1h").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna(),
        "15M": ts_15m, "1M": ts_1m
    }


def run_scanner():
    engine = SMCTradingEngine(min_rr=2.0, max_rr=8.0, atr_multiplier=0.3)
    initialize_trade_history()
    print("==================================================\n  OPTIMIZED SMC EXECUTION SCANNER (EUR/USD & XAU/USD)\n==================================================")

    while True:
        manage_log_size()
        now_ist = datetime.now(IST)

        if NEWS_PAUSE or not is_active_session(now_ist) or check_daily_circuit_breaker():
            time.sleep(IDLE_SLEEP_SECONDS)
            continue

        now_str = now_ist.strftime("%Y-%m-%d %I:%M:%S %p IST")

        for idx, symbol in enumerate(TICKERS):
            try:
                cfg = ASSET_CONFIG[symbol]
                contract_size, quote_usd, asset_name = cfg["contract_size"], cfg["quote_usd"], cfg["name"]

                print(f"\n🎯 PROCESSING: {symbol} ({asset_name})")
                data = fetch_realtime_data(symbol)
                latest_price = data["1M"]["close"].iloc[-1]
                atr_val = calculate_atr(data["15M"])

                evaluate_pending_trades(data["1M"]["high"].iloc[-1], data["1M"]["low"].iloc[-1], atr_val, now_str)

                result = engine.analyze(data)
                decision, reason = result.get("decision", "NO_TRADE"), result.get("reason", "Setup validated")
                print(f"🚦 Decision: {decision} | Status: {reason}")

                tp = result.get("trade_params")
                if decision in ["BUY", "SELL"] and tp:
                    entry, sl, tp1, tp2, rr = tp["entry"], tp["sl"], tp["tp1"], tp["tp2"], tp["rr"]
                    risk_pts, rew_tp1, rew_tp2 = abs(entry - sl), abs(tp1 - entry), abs(tp2 - entry)

                    # Multi-lot simulation calculations
                    lots_list = [0.01, 0.02, 0.03, 0.05, 0.10, 0.50]
                    sim_rows = []
                    for lot in lots_list:
                        factor = lot * contract_size if quote_usd else lot * contract_size / latest_price
                        sim_rows.append(f"`{lot:.2f}L | -${risk_pts * factor:.2f} | +${rew_tp1 * factor:.2f} | +${rew_tp2 * factor:.2f}`")

                    risk_per_lot = risk_pts * contract_size if quote_usd else contract_size * (risk_pts / latest_price)
                    
                    if (risk_per_lot * 0.01) > MAX_DOLLAR_RISK:
                        print(f"❌ REJECTED: Min risk exceeds MAX_DOLLAR_RISK.")
                        continue
                    if rr < MIN_REQUIRED_RR:
                        print(f"❌ REJECTED: R:R ({rr:.2f}R) below minimum.")
                        continue

                    rec_lots = max(0.01, math.floor((MAX_DOLLAR_RISK / risk_per_lot) * 100) / 100)
                    actual_risk = rec_lots * risk_per_lot

                    has_active = False
                    if os.path.exists(TRADE_HISTORY_FILE):
                        df_chk = pd.read_csv(TRADE_HISTORY_FILE)
                        has_active = not df_chk[(df_chk["status"] == "PENDING") & (df_chk["symbol"] == symbol)].empty

                    if not has_active:
                        trade_id = f"{symbol.replace('/', '')}_{now_ist.strftime('%Y%m%d_%H%M%S')}"
                        
                        # Append trade log
                        pd.concat([pd.read_csv(TRADE_HISTORY_FILE), pd.DataFrame([{
                            "trade_id": trade_id, "timestamp": now_str, "symbol": symbol, "decision": decision,
                            "entry": entry, "sl": sl, "tp1": tp1, "tp2": tp2, "lots": rec_lots, "status": "PENDING", "exit_time": "N/A", "be_active": 0
                        }])], ignore_index=True).to_csv(TRADE_HISTORY_FILE, index=False)

                        send_telegram_alert(
                            f"🚨 *SMC SIGNAL: {symbol}* (`{trade_id}`)\n\n"
                            f"• *Decision:* `{decision}` | *Price:* `{latest_price}`\n"
                            f"• *Entry:* `{entry}` | *SL:* `{sl}`\n"
                            f"• *TP1:* `{tp1}` | *TP2:* `{tp2}`\n"
                            f"• *Lots:* `{rec_lots}` (Risk: `${actual_risk:.2f}` | R:R: `{rr:.2f}R`)\n\n"
                            f"💰 *Multi-Lot Table:*\n" + "\n".join(sim_rows) + f"\n\n• *Time:* `{now_str}`"
                        )
                    else:
                        print(f"⏳ Active PENDING trade exists for {symbol}.")

            except Exception as e:
                print(f"[{symbol}] Error: {e}")

            if idx < len(TICKERS) - 1:
                time.sleep(API_THROTTLE_SECONDS)

        time.sleep(SCAN_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_scanner()