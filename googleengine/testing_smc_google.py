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
NEWS_PAUSE = False                      # Set to True to halt scanning during high-impact news

# Risk Parameters for Flexible Sizing & Safety
MIN_REQUIRED_RR = 2.0                   # Minimum acceptable Reward-to-Risk ratio for Target 2
MAX_DAILY_LOSSES = 2                    # Circuit breaker limit: stop trading after X losses in a day

# Multi-Asset Configuration (EUR/USD and XAU/USD)
ASSET_CONFIG = {
    "XAU/USD": {"contract_size": 100, "quote_usd": True, "name": "Gold"},
    "EUR/USD": {"contract_size": 100000, "quote_usd": True, "name": "Euro / US Dollar"}
}

# Dual-Key Failover System Setup
TWELVE_DATA_API_KEY_1 = os.getenv("TWELVE_DATA_API_KEY_1")
TWELVE_DATA_API_KEY_2 = os.getenv("TWELVE_DATA_API_KEY_2")

# Backward compatibility fallback if user only set the old generic key name
if not TWELVE_DATA_API_KEY_1:
    TWELVE_DATA_API_KEY_1 = os.getenv("TWELVE_DATA_API_KEY")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TWELVE_DATA_API_KEY_1:
    print("❌ Error: TWELVE_DATA_API_KEY_1 or TWELVE_DATA_API_KEY environment variable is not set.")
    sys.exit(1)

TICKERS = ["XAU/USD", "EUR/USD"]
SCAN_INTERVAL_SECONDS = 180  # 3 minutes cycle rotation
API_THROTTLE_SECONDS = 15    # Pause between tickers to respect Twelve Data limits
IDLE_SLEEP_SECONDS = 300     # 5 minutes
IST = ZoneInfo("Asia/Kolkata")
TRADE_HISTORY_FILE = "trade_history.csv"
MISTAKE_JOURNAL_FILE = "mistake_journal.csv"
LOG_FILE = "scanner.log"

# Active API Key Tracking State
current_api_key_index = 1
active_td_client = TDClient(apikey=TWELVE_DATA_API_KEY_1)


def switch_twelve_data_key():
    """Switches to the secondary Twelve Data API key upon hitting rate limits."""
    global current_api_key_index, active_td_client
    if current_api_key_index == 1 and TWELVE_DATA_API_KEY_2:
        current_api_key_index = 2
        active_td_client = TDClient(apikey=TWELVE_DATA_API_KEY_2)
        print("🔄 [API FAILOVER] Primary key hit daily credit limit. Successfully switched to TWELVE_DATA_API_KEY_2!")
        send_telegram_alert("🔄 *API FAILOVER NOTICE*\nPrimary Twelve Data key hit credit limits. Successfully rotated to **Key #2**.")
        return True
    elif current_api_key_index == 2:
        print("⚠️ [API FAILOVER] Both keys are currently exhausted or encountering errors.")
        return False
    else:
        print("⚠️ [API FAILOVER] Second API key is not configured in environment variables.")
        return False


def execute_with_failover(func, *args, **kwargs):
    """Executes a Twelve Data API call, automatically handling credit limits and failing over."""
    global active_td_client
    try:
        return func(*args, **kwargs)
    except Exception as e:
        err_msg = str(e).lower()
        if "credit" in err_msg or "limit" in err_msg or "rate" in err_msg or "exhausted" in err_msg:
            print(f"⚠️ Twelve Data Rate Limit / Credit error detected: {e}")
            if switch_twelve_data_key():
                # Retry once with the new key
                return func(*args, **kwargs)
        raise e


def manage_log_size():
    """Prevents scanner.log from bloating server memory/disk (Max 5MB limit)."""
    if os.path.exists(LOG_FILE):
        if os.path.getsize(LOG_FILE) > 5 * 1024 * 1024:
            with open(LOG_FILE, "w") as f:
                f.write(f"[{datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')}] Log rotated due to size limit.\n")


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
    """Initializes trade history CSV and prints historical stats on boot."""
    if not os.path.exists(TRADE_HISTORY_FILE):
        pd.DataFrame(columns=[
            "trade_id", "timestamp", "symbol", "decision", "entry", "sl", "tp1", "tp2", "lots", "status", "exit_time", "be_active", "pnl_usd"
        ]).to_csv(TRADE_HISTORY_FILE, index=False)
    else:
        df = pd.read_csv(TRADE_HISTORY_FILE)
        if "pnl_usd" not in df.columns:
            df["pnl_usd"] = 0.0
            df.to_csv(TRADE_HISTORY_FILE, index=False)

        closed_trades = df[df["status"] != "PENDING"]
        if not closed_trades.empty:
            wins = len(closed_trades[closed_trades["status"] == "WIN"])
            losses = len(closed_trades[closed_trades["status"] == "LOSS"])
            total = len(closed_trades)
            win_rate = (wins / total) * 100 if total > 0 else 0
            total_pnl = closed_trades["pnl_usd"].sum()
            print(f"📈 [PERFORMANCE REVIEW] Total Closed: {total} | Wins: {wins} | Losses: {losses} | Win Rate: {win_rate:.1f}% | Net PnL: ${total_pnl:.2f}")


def check_daily_circuit_breaker() -> bool:
    """Returns True if MAX_DAILY_LOSSES has been reached today, halting new trades."""
    if not os.path.exists(TRADE_HISTORY_FILE):
        return False
    today_str = datetime.now(IST).strftime("%Y-%m-%d")
    df = pd.read_csv(TRADE_HISTORY_FILE)
    if "exit_time" not in df.columns or "status" not in df.columns:
        return False
    
    losses_today = df[(df["status"] == "LOSS") & (df["exit_time"].str.startswith(today_str, na=False))]
    if len(losses_today) >= MAX_DAILY_LOSSES:
        print(f"🔴 [CIRCUIT BREAKER] {len(losses_today)} losses recorded today. Halting new trade executions.")
        return True
    return False


def log_new_trade(trade_id, timestamp, symbol, decision, entry, sl, tp1, tp2, lots):
    """Logs a newly triggered trade into trade_history.csv."""
    initialize_trade_history()
    df = pd.read_csv(TRADE_HISTORY_FILE)
    new_row = {
        "trade_id": trade_id, "timestamp": timestamp, "symbol": symbol, "decision": decision,
        "entry": entry, "sl": sl, "tp1": tp1, "tp2": tp2, "lots": lots, "status": "PENDING", "exit_time": "N/A", "be_active": 0, "pnl_usd": 0.0
    }
    pd.concat([df, pd.DataFrame([new_row])], ignore_index=True).to_csv(TRADE_HISTORY_FILE, index=False)


def log_trade_mistake(trade_id, symbol, decision, entry, sl, exit_price, atr_val, now_str):
    """Logs detailed autopsy data for a losing trade into mistake_journal.csv for future analysis."""
    file_exists = os.path.exists(MISTAKE_JOURNAL_FILE)
    points_lost = abs(exit_price - entry)
    
    row_data = {
        "trade_id": trade_id,
        "timestamp": now_str,
        "symbol": symbol,
        "decision": decision,
        "entry_price": entry,
        "stop_loss": sl,
        "exit_price": exit_price,
        "atr_at_entry": atr_val,
        "points_lost": round(points_lost, 5)
    }
    
    df_new = pd.DataFrame([row_data])
    if not file_exists:
        df_new.to_csv(MISTAKE_JOURNAL_FILE, index=False)
    else:
        df_new.to_csv(MISTAKE_JOURNAL_FILE, mode='a', header=False, index=False)
    print(f"📝 [MISTAKE JOURNAL] Logged autopsy for failed trade ID: {trade_id} ({symbol})")


def check_and_send_monthly_report(now_ist: datetime):
    """Checks if today is the 1st day of a new month and generates/sends the previous month's report."""
    report_flag_file = "last_monthly_report.txt"
    current_month_str = now_ist.strftime("%Y-%m")
    
    if now_ist.day == 1:
        last_sent = ""
        if os.path.exists(report_flag_file):
            with open(report_flag_file, "r") as f:
                last_sent = f.read().strip()
                
        if last_sent != current_month_str:
            if os.path.exists(TRADE_HISTORY_FILE):
                df = pd.read_csv(TRADE_HISTORY_FILE)
                closed = df[df["status"] != "PENDING"].copy()
                
                if not closed.empty:
                    prev_month_dt = now_ist.replace(day=1) - pd.Timedelta(days=1)
                    prev_month_str = prev_month_dt.strftime("%Y-%m")
                    
                    closed["exit_date"] = pd.to_datetime(closed["exit_time"], errors="coerce")
                    month_trades = closed[closed["exit_date"].dt.strftime("%Y-%m") == prev_month_str]
                    
                    if not month_trades.empty:
                        total_trades = len(month_trades)
                        wins = len(month_trades[month_trades["status"] == "WIN"])
                        losses = len(month_trades[month_trades["status"] == "LOSS"])
                        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
                        net_pnl = month_trades["pnl_usd"].sum()
                        emoji = "🟢" if net_pnl >= 0 else "🔴"
                        
                        report_msg = (
                            f"📊 *MONTHLY PERFORMANCE REPORT ({prev_month_str})* 📊\n\n"
                            f"• *Total Trades Taken:* `{total_trades}`\n"
                            f"• *Winning Trades:* `{wins}` 🟢\n"
                            f"• *Losing Trades:* `{losses}` ❌\n"
                            f"• *Win Rate:* `{win_rate:.1f}%`\n"
                            f"• *Net Month-End PnL:* {emoji} *`${net_pnl:.2f}`*\n\n"
                            f"_Report generated automatically at month start._"
                        )
                        send_telegram_alert(report_msg)
                        
            with open(report_flag_file, "w") as f:
                f.write(current_month_str)


def evaluate_pending_trades(current_high: float, current_low: float, atr_val: float, now_str: str, symbol: str, quote_usd: bool, contract_size: float):
    """Monitors pending trades, manages Breakeven activation, checks SL/TP hits, and computes dollar PnL."""
    if not os.path.exists(TRADE_HISTORY_FILE):
        return
    df = pd.read_csv(TRADE_HISTORY_FILE)
    updated = False

    for idx, row in df.iterrows():
        if row["status"] == "PENDING" and row["symbol"] == symbol:
            decision = row["decision"]
            entry = float(row["entry"])
            sl = float(row["sl"])
            tp1 = float(row["tp1"])
            tp2 = float(row["tp2"])
            lots = float(row["lots"])
            trade_id = row["trade_id"]
            be_active = int(row.get("be_active", 0))

            if decision == "BUY":
                if current_high >= tp1 and be_active == 0:
                    df.at[idx, "sl"] = entry
                    df.at[idx, "be_active"] = 1
                    updated = True
                    send_telegram_alert(f"🛡️ *Breakeven Activated* for Trade **{symbol}** BUY (`{trade_id}`).\nStop Loss moved to entry price: `{entry}`")

                if current_low <= float(df.at[idx, "sl"]):
                    actual_exit_sl = float(df.at[idx, "sl"])
                    risk_points_realized = abs(entry - actual_exit_sl) if be_active == 1 else abs(entry - sl)
                    
                    if quote_usd:
                        pnl = -(lots * risk_points_realized * contract_size) if be_active == 0 else 0.0
                    else:
                        pnl = -(lots * contract_size * (risk_points_realized / current_low)) if be_active == 0 else 0.0

                    df.at[idx, "status"] = "LOSS" if be_active == 0 else "BREAKEVEN"
                    df.at[idx, "exit_time"] = now_str
                    df.at[idx, "pnl_usd"] = round(pnl, 2)
                    updated = True
                    
                    send_telegram_alert(f"❌ *TRADE STOPPED OUT* [Trade: **{symbol}**]\nID: `{trade_id}`\nResult PnL: `${pnl:.2f}`")
                    log_trade_mistake(trade_id, symbol, decision, entry, sl, current_low, atr_val, now_str)

                elif current_high >= tp2:
                    reward_points = abs(tp2 - entry)
                    if quote_usd:
                        pnl = lots * reward_points * contract_size
                    else:
                        pnl = lots * contract_size * (reward_points / current_high)

                    df.at[idx, "status"] = "WIN"
                    df.at[idx, "exit_time"] = now_str
                    df.at[idx, "pnl_usd"] = round(pnl, 2)
                    updated = True
                    
                    send_telegram_alert(f"🎯 *TARGET REACHED (WIN)* [Trade: **{symbol}**]\nID: `{trade_id}`\nHitting TP2 at `{tp2}`\nProfit PnL: *+${pnl:.2f}*")

            elif decision == "SELL":
                if current_low <= tp1 and be_active == 0:
                    df.at[idx, "sl"] = entry
                    df.at[idx, "be_active"] = 1
                    updated = True
                    send_telegram_alert(f"🛡️ *Breakeven Activated* for Trade **{symbol}** SELL (`{trade_id}`).\nStop Loss moved to entry price: `{entry}`")

                if current_high >= float(df.at[idx, "sl"]):
                    actual_exit_sl = float(df.at[idx, "sl"])
                    risk_points_realized = abs(actual_exit_sl - entry) if be_active == 1 else abs(sl - entry)

                    if quote_usd:
                        pnl = -(lots * risk_points_realized * contract_size) if be_active == 0 else 0.0
                    else:
                        pnl = -(lots * contract_size * (risk_points_realized / current_high)) if be_active == 0 else 0.0

                    df.at[idx, "status"] = "LOSS" if be_active == 0 else "BREAKEVEN"
                    df.at[idx, "exit_time"] = now_str
                    df.at[idx, "pnl_usd"] = round(pnl, 2)
                    updated = True
                    
                    send_telegram_alert(f"❌ *TRADE STOPPED OUT* [Trade: **{symbol}**]\nID: `{trade_id}`\nResult PnL: `${pnl:.2f}`")
                    log_trade_mistake(trade_id, symbol, decision, entry, sl, current_high, atr_val, now_str)

                elif current_low <= tp2:
                    reward_points = abs(entry - tp2)
                    if quote_usd:
                        pnl = lots * reward_points * contract_size
                    else:
                        pnl = lots * contract_size * (reward_points / current_low)

                    df.at[idx, "status"] = "WIN"
                    df.at[idx, "exit_time"] = now_str
                    df.at[idx, "pnl_usd"] = round(pnl, 2)
                    updated = True
                    
                    send_telegram_alert(f"🎯 *TARGET REACHED (WIN)* [Trade: **{symbol}**]\nID: `{trade_id}`\nHitting TP2 at `{tp2}`\nProfit PnL: *+${pnl:.2f}*")

    if updated:
        df.to_csv(TRADE_HISTORY_FILE, index=False)


def find_macro_4h_range(df: pd.DataFrame, lookback: int = 50):
    macro_df = df.tail(lookback)
    macro_sh = macro_df["high"].max()
    macro_sl = macro_df["low"].min()
    return macro_sh, macro_sl


def calculate_atr(df: pd.DataFrame, period: int = 14) -> float:
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    return float(true_range.rolling(period).mean().iloc[-1])


def fetch_realtime_data(symbol: str) -> dict:
    def _fetch():
        ts_15m = active_td_client.time_series(symbol=symbol, interval="15min", outputsize=500, timezone="UTC").as_pandas()
        ts_1m = active_td_client.time_series(symbol=symbol, interval="1min", outputsize=100, timezone="UTC").as_pandas()
        return ts_15m, ts_1m

    ts_15m, ts_1m = execute_with_failover(_fetch)

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
    engine = SMCTradingEngine(min_rr=2.0, max_rr=8.0, atr_multiplier=0.5)
    initialize_trade_history()

    print("==================================================")
    print("  UPGRADED SMC EXECUTION SCANNER (EUR/USD & XAU/USD)")
    print("==================================================\n")

    while True:
        manage_log_size()
        now_ist = datetime.now(IST)

        check_and_send_monthly_report(now_ist)

        if NEWS_PAUSE:
            print(f"[{now_ist.strftime('%I:%M:%S %p IST')}] 🛑 NEWS PAUSE ACTIVE. Idling...")
            time.sleep(IDLE_SLEEP_SECONDS)
            continue

        if not is_active_session(now_ist):
            print(f"[{now_ist.strftime('%I:%M:%S %p IST')}] 😴 Session Closed. Idling...")
            time.sleep(IDLE_SLEEP_SECONDS)
            continue

        if check_daily_circuit_breaker():
            time.sleep(IDLE_SLEEP_SECONDS)
            continue

        now_str = now_ist.strftime("%Y-%m-%d %I:%M:%S %p IST")

        for idx, symbol in enumerate(TICKERS):
            try:
                cfg = ASSET_CONFIG.get(symbol, {"contract_size": 100000, "quote_usd": True, "name": symbol})
                contract_size = cfg["contract_size"]
                quote_usd = cfg["quote_usd"]
                asset_name = cfg["name"]

                data = fetch_realtime_data(symbol)
                latest_price = data["1M"]["close"].iloc[-1]
                atr_val = calculate_atr(data["15M"], period=14)

                evaluate_pending_trades(data["1M"]["high"].iloc[-1], data["1M"]["low"].iloc[-1], atr_val, now_str, symbol, quote_usd, contract_size)

                h4_sh, h4_sl = find_macro_4h_range(data["4H"], lookback=50)
                eq_4h = (h4_sh + h4_sl) / 2

                result = engine.analyze(data)
                decision = result.get("decision", "NO_TRADE")
                reason = result.get("reason", "Setup validated")
                trade_params = result.get("trade_params")

                # Fallback execution map when engine is in WAIT mode
                if not trade_params:
                    is_bearish = "SELL" in reason.upper() or "BEARISH" in reason.upper() or "NOT YET IN" in reason.upper()
                    
                    if is_bearish:
                        sim_sl = latest_price + (atr_val * 0.5)
                        sim_tp1 = latest_price - (atr_val * 1.2)
                        sim_tp2 = latest_price - (atr_val * 3.0)
                    else:
                        sim_sl = latest_price - (atr_val * 0.5)
                        sim_tp1 = latest_price + (atr_val * 1.2)
                        sim_tp2 = latest_price + (atr_val * 3.0)
                        
                    sim_rr = abs(sim_tp2 - latest_price) / abs(latest_price - sim_sl) if abs(latest_price - sim_sl) > 0 else 5.0
                    
                    trade_params = {
                        "entry": round(latest_price, 5),
                        "sl": round(sim_sl, 5),
                        "tp1": round(sim_tp1, 5),
                        "tp2": round(sim_tp2, 5),
                        "rr": round(sim_rr, 2)
                    }

                print("==================================================")
                print(f"🎯 PROCESSING TRADE ASSET: {symbol} ({asset_name})")
                print("==================================================")
                print(f"📊 LIVE SCANNER REPORT FOR TRADE: {symbol} ({asset_name})")
                print(f"⏰ Scan Time (IST):  {now_str}")
                print(f"💲 Live Price:       {latest_price}")
                print(f"🚦 Engine Decision:  {reason}")
                print("==================================================\n")
                print(f"1️⃣  4H MACRO BIAS & 15M STRUCTURAL CONTEXT")
                print(f"   • Active Trade:   {symbol} ({asset_name})")
                print(f"   • 4H Equilibrium: {eq_4h}")
                print(f"   • Overall Bias:   N/A")
                print(f"   • 15M ATR (Noise):{atr_val}")
                print("--------------------------------------------------\n")

                planned_entry = trade_params["entry"]
                planned_sl = trade_params["sl"]
                planned_tp1 = trade_params["tp1"]
                planned_tp2 = trade_params["tp2"]
                rr_tp2 = trade_params["rr"]

                risk_points = abs(planned_entry - planned_sl)
                reward_tp1 = abs(planned_tp1 - planned_entry)
                reward_tp2 = abs(planned_tp2 - planned_entry)

                direction_str = "SHORT (Bearish Reversal from Premium)" if decision != "BUY" else "LONG (Bullish Reversal from Discount)"

                print(f"2️⃣  TIGHTER 15M PREDICTIVE EXECUTION MAP [{symbol}]")
                print(f"   • Active Trade:    {symbol} ({asset_name})")
                print(f"   • Direction:       {direction_str}")
                print(f"   • Target Entry:    {planned_entry}")
                print(f"   • Logical SL:      {planned_sl}")
                print(f"   • Target 1 (15M):  {planned_tp1}")
                print(f"   • Target 2 (1H):   {planned_tp2} -> R:R {rr_tp2}R")
                print("--------------------------------------------------\n")

                # Risk & Lot Sizing Scenario Matrix (Informational for discretion)
                print(f"💰 RISK & LOT SIZING MATRIX [Trade: {symbol} - {asset_name}]")
                print("==================================================")
                print("   Lot Size   |   SL Loss    |   TP1 Profit (1.2x)|   TP2 Profit")
                print("--------------------------------------------------")
                for lot in [0.01, 0.02, 0.05, 0.10, 0.50, 1.00]:
                    if quote_usd:
                        sl_loss = lot * risk_points * contract_size
                        tp1_prof = lot * reward_tp1 * contract_size
                        tp2_prof = lot * reward_tp2 * contract_size
                    else:
                        sl_loss = lot * contract_size * (risk_points / latest_price)
                        tp1_prof = lot * contract_size * (reward_tp1 / latest_price)
                        tp2_prof = lot * contract_size * (reward_tp2 / latest_price)
                    print(f"   {lot:4.2f} Lots  |   -${sl_loss:.2f}   |   +${tp1_prof:.2f}       |   +${tp2_prof:.2f}")
                print("==================================================\n")

                if decision in ["BUY", "SELL"]:
                    if rr_tp2 < MIN_REQUIRED_RR:
                        print(f"   ❌ REJECTED [{symbol}]: R:R ({rr_tp2}R) is below minimum required {MIN_REQUIRED_RR}R.")
                    else:
                        default_lots = 0.01
                        if quote_usd:
                            actual_dollar_risk = default_lots * risk_points * contract_size
                        else:
                            actual_dollar_risk = default_lots * contract_size * (risk_points / latest_price)

                        print(f"   ✔ APPROVED [{symbol}]: Structural setup verified within SMC criteria.")
                        print(f"   • Baseline Execution: {default_lots} Lot (SL Risk: ${actual_dollar_risk:.2f} | R:R: {rr_tp2}R)")

                        has_active_trade = False
                        if os.path.exists(TRADE_HISTORY_FILE):
                            df_check = pd.read_csv(TRADE_HISTORY_FILE)
                            if not df_check.empty and "status" in df_check.columns:
                                has_active_trade = not df_check[(df_check["status"] == "PENDING") & (df_check["symbol"] == symbol)].empty

                        if not has_active_trade:
                            trade_id = f"{symbol.replace('/', '')}_{now_ist.strftime('%Y%m%d_%H%M%S')}"
                            log_new_trade(trade_id, now_str, symbol, decision, planned_entry, planned_sl, planned_tp1, planned_tp2, default_lots)
                            
                            alert_msg = (
                                f"🚨 *SMC TRADE TRIGGERED* [{symbol}]\n\n"
                                f"• *Direction:* `{decision}`\n"
                                f"• *Entry:* `{planned_entry}`\n"
                                f"• *Structural SL:* `{planned_sl}`\n"
                                f"• *TP1 (1.2x ATR):* `{planned_tp1}`\n"
                                f"• *TP2 (1H Liquidity):* `{planned_tp2}` (`{rr_tp2}R`)\n"
                                f"• *Baseline Risk (0.01 Lot):* `${actual_dollar_risk:.2f}`"
                            )
                            send_telegram_alert(alert_msg)
                else:
                    print(f"   ⏳ STATUS: Monitoring structure. Awaiting valid liquidity sweep for execution.")

            except Exception as e:
                print(f"[{symbol}] Error fetching data: {e}")

            if idx < len(TICKERS) - 1:
                time.sleep(API_THROTTLE_SECONDS)

        time.sleep(SCAN_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_scanner()