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

# Risk Parameters for Lot Sizing & Safety
MAX_DOLLAR_RISK = 10.0                  # Maximum allowed loss in USD per trade
MIN_REQUIRED_RR = 2.0                   # Minimum acceptable Reward-to-Risk ratio for Target 2
MAX_DAILY_LOSSES = 2                    # Circuit breaker limit: stop trading after X losses in a day

# Multi-Asset Configuration (Contract sizes & descriptive asset names)
ASSET_CONFIG = {
    "XAU/USD": {"contract_size": 100, "name": "Gold"},
    "EUR/USD": {"contract_size": 100000, "name": "Euro / US Dollar"},
    "USD/JPY": {"contract_size": 100000, "name": "US Dollar / Japanese Yen"}
}

TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TWELVE_DATA_API_KEY:
    print("❌ Error: TWELVE_DATA_API_KEY environment variable is not set.")
    sys.exit(1)

TICKERS = ["XAU/USD", "EUR/USD", "USD/JPY"]
SCAN_INTERVAL_SECONDS = 180  # 3 minutes cycle for multi-ticker rotation
API_THROTTLE_SECONDS = 15    # Pause between tickers to respect Twelve Data API limits
IDLE_SLEEP_SECONDS = 300     # 5 minutes
IST = ZoneInfo("Asia/Kolkata")
TRADE_HISTORY_FILE = "trade_history.csv"
MISTAKE_JOURNAL_FILE = "mistake_journal.csv"
LOG_FILE = "scanner.log"

td = TDClient(apikey=TWELVE_DATA_API_KEY)


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
            "trade_id", "timestamp", "symbol", "decision", "entry", "sl", "tp1", "tp2", "lots", "status", "exit_time", "be_active"
        ]).to_csv(TRADE_HISTORY_FILE, index=False)
    else:
        df = pd.read_csv(TRADE_HISTORY_FILE)
        closed_trades = df[df["status"] != "PENDING"]
        if not closed_trades.empty:
            wins = len(closed_trades[closed_trades["status"] == "WIN"])
            losses = len(closed_trades[closed_trades["status"] == "LOSS"])
            total = len(closed_trades)
            win_rate = (wins / total) * 100 if total > 0 else 0
            print(f"📈 [PERFORMANCE REVIEW] Total Closed: {total} | Wins: {wins} | Losses: {losses} | Win Rate: {win_rate:.1f}%")


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
        "entry": entry, "sl": sl, "tp1": tp1, "tp2": tp2, "lots": lots, "status": "PENDING", "exit_time": "N/A", "be_active": 0
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


def evaluate_pending_trades(current_high: float, current_low: float, atr_val: float, now_str: str):
    """Monitors pending trades, manages Breakeven activation, checks SL/TP hits, and logs losses."""
    if not os.path.exists(TRADE_HISTORY_FILE):
        return
    df = pd.read_csv(TRADE_HISTORY_FILE)
    updated = False

    for idx, row in df.iterrows():
        if row["status"] == "PENDING":
            decision = row["decision"]
            entry = float(row["entry"])
            sl = float(row["sl"])
            tp1 = float(row["tp1"])
            tp2 = float(row["tp2"])
            trade_id = row["trade_id"]
            symbol = row["symbol"]
            be_active = int(row.get("be_active", 0))

            if decision == "BUY":
                if current_high >= tp1 and be_active == 0:
                    df.at[idx, "sl"] = entry
                    df.at[idx, "be_active"] = 1
                    updated = True
                    send_telegram_alert(f"🛡️ *Breakeven Activated* for Trade **{symbol}** BUY (`{trade_id}`).\nStop Loss moved to entry price: `{entry}`")

                if current_low <= float(df.at[idx, "sl"]):
                    df.at[idx, "status"] = "LOSS"
                    df.at[idx, "exit_time"] = now_str
                    updated = True
                    send_telegram_alert(f"❌ *TRADE STOPPED OUT (LOSS)* [Trade: **{symbol}**]\nID: `{trade_id}`\nHitting SL at `{float(df.at[idx, 'sl'])}`")
                    log_trade_mistake(trade_id, symbol, decision, entry, sl, current_low, atr_val, now_str)

                elif current_high >= tp2:
                    df.at[idx, "status"] = "WIN"
                    df.at[idx, "exit_time"] = now_str
                    updated = True
                    send_telegram_alert(f"🎯 *TARGET REACHED (WIN)* [Trade: **{symbol}**]\nID: `{trade_id}`\nHitting TP2 at `{tp2}`")

            elif decision == "SELL":
                if current_low <= tp1 and be_active == 0:
                    df.at[idx, "sl"] = entry
                    df.at[idx, "be_active"] = 1
                    updated = True
                    send_telegram_alert(f"🛡️ *Breakeven Activated* for Trade **{symbol}** SELL (`{trade_id}`).\nStop Loss moved to entry price: `{entry}`")

                if current_high >= float(df.at[idx, "sl"]):
                    df.at[idx, "status"] = "LOSS"
                    df.at[idx, "exit_time"] = now_str
                    updated = True
                    send_telegram_alert(f"❌ *TRADE STOPPED OUT (LOSS)* [Trade: **{symbol}**]\nID: `{trade_id}`\nHitting SL at `{float(df.at[idx, 'sl'])}`")
                    log_trade_mistake(trade_id, symbol, decision, entry, sl, current_high, atr_val, now_str)

                elif current_low <= tp2:
                    df.at[idx, "status"] = "WIN"
                    df.at[idx, "exit_time"] = now_str
                    updated = True
                    send_telegram_alert(f"🎯 *TARGET REACHED (WIN)* [Trade: **{symbol}**]\nID: `{trade_id}`\nHitting TP2 at `{tp2}`")

    if updated:
        df.to_csv(TRADE_HISTORY_FILE, index=False)


def find_macro_4h_range(df: pd.DataFrame, lookback: int = 50):
    """Identifies the true macro 4H Dealing Range (Highest High and Lowest Low over a structural lookback)."""
    macro_df = df.tail(lookback)
    macro_sh = macro_df["high"].max()
    macro_sl = macro_df["low"].min()
    return macro_sh, macro_sl


def find_smc_swings(df: pd.DataFrame, window: int = 2):
    """Identifies verified SMC Fractal Swing Highs and Swing Lows for 1H liquidity."""
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

    print("==================================================")
    print("  MULTI-ASSET SMC SCANNER v2.8 (Explicit Trades) ")
    print("==================================================")

    while True:
        manage_log_size()
        now_ist = datetime.now(IST)

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
                cfg = ASSET_CONFIG.get(symbol, {"contract_size": 100000, "name": symbol})
                contract_size = cfg["contract_size"]
                asset_name = cfg["name"]

                print("\n==================================================")
                print(f"🎯 PROCESSING TRADE ASSET: {symbol} ({asset_name})")
                print("==================================================")

                data = fetch_realtime_data(symbol)
                latest_price = data["1M"]["close"].iloc[-1]
                atr_val = calculate_atr(data["1H"], period=14)

                evaluate_pending_trades(data["1M"]["high"].iloc[-1], data["1M"]["low"].iloc[-1], atr_val, now_str)

                h4_sh, h4_sl = find_macro_4h_range(data["4H"], lookback=50)
                eq_4h = (h4_sh + h4_sl) / 2
                h1_bsl, h1_ssl = find_smc_swings(data["1H"], window=2)

                result = engine.analyze(data)
                decision = result.get("decision", "NO_TRADE")
                reason = result.get("reason", "Setup validated")
                bias = result.get("bias_4h", "N/A")

                print(f"📊 LIVE SCANNER REPORT FOR TRADE: {symbol} ({asset_name})")
                print(f"⏰ Scan Time (IST):  {now_str}")
                print(f"💲 Live Price:       {latest_price}")
                print(f"🚦 Engine Decision:  {decision} ({reason})")
                print("==================================================")
                print("1️⃣  4H MACRO DEALING RANGE & BIAS")
                print(f"   • Active Trade:   {symbol} ({asset_name})")
                print(f"   • 4H Swing High:  {h4_sh}")
                print(f"   • 4H Swing Low:   {h4_sl}")
                print(f"   • Equilibrium:    {eq_4h}")
                print(f"   • Overall Bias:   {bias}")
                print(f"   • 1H ATR (Noise): {atr_val}")
                print("--------------------------------------------------")
                print(f"2️⃣  PREDICTIVE EXECUTION MAP [{symbol} - {asset_name}]")

                if latest_price > eq_4h:
                    # SHORT SETUP
                    planned_entry = h1_bsl
                    structural_ceiling = max(h4_sh, h1_bsl)
                    planned_sl = structural_ceiling + (atr_val * 0.5)
                    planned_tp1 = eq_4h
                    planned_tp2 = h4_sl
                    risk_points = planned_sl - planned_entry
                    reward_tp1 = planned_entry - planned_tp1
                    reward_tp2 = planned_entry - planned_tp2
                    rr_tp2 = reward_tp2 / risk_points if risk_points > 0 else 0

                    print(f"   • Active Trade:    {symbol} ({asset_name})")
                    print("   • Direction:       SHORT (Bearish Reversal from Premium)")
                    print(f"   • Target Entry:    {planned_entry} (1H BSL Fractal High Sweep)")
                    print(f"   • 📈 CHART TIP:    Draw horizontal line at {planned_entry} on your 1H chart to watch the sweep!")
                    print(f"   • Logical SL:      {planned_sl} (Structural Ceiling + 0.5*ATR)")
                    print(f"   • Target 1 (EQ):   {planned_tp1}")
                    print(f"   • Target 2 (4H SL):{planned_tp2} -> R:R {rr_tp2:.2f}R")
                else:
                    # LONG SETUP
                    planned_entry = h1_ssl
                    structural_floor = min(h4_sl, h1_ssl)
                    planned_sl = structural_floor - (atr_val * 0.5)
                    planned_tp1 = eq_4h
                    planned_tp2 = h4_sh
                    risk_points = planned_entry - planned_sl
                    reward_tp1 = planned_tp1 - planned_entry
                    reward_tp2 = planned_tp2 - planned_entry
                    rr_tp2 = reward_tp2 / risk_points if risk_points > 0 else 0

                    print(f"   • Active Trade:    {symbol} ({asset_name})")
                    print("   • Direction:       LONG (Bullish Reversal from Discount)")
                    print(f"   • Target Entry:    {planned_entry} (1H SSL Fractal Low Sweep)")
                    print(f"   • 📈 CHART TIP:    Draw horizontal line at {planned_entry} on your 1H chart to watch the sweep!")
                    print(f"   • Logical SL:      {planned_sl} (Structural Floor - 0.5*ATR)")
                    print(f"   • Target 1 (EQ):   {planned_tp1}")
                    print(f"   • Target 2 (4H SH):{planned_tp2} -> R:R {rr_tp2:.2f}R")

                # MULTI-LOT SCENARIO SIMULATOR TABLE (CONSOLE)
                print("--------------------------------------------------")
                print(f"💰 MULTI-LOT SCENARIO SIMULATOR [Trade: {symbol} - {asset_name}]")
                print("==================================================")
                print("   Lot Size   |   SL Loss    |   TP1 Profit (EQ) |   TP2 Profit")
                print("--------------------------------------------------")
                for lot in [0.01, 0.02, 0.03, 0.05, 0.10]:
                    sl_loss = lot * risk_points * contract_size
                    tp1_prof = lot * reward_tp1 * contract_size
                    tp2_prof = lot * reward_tp2 * contract_size
                    print(f"   {lot:4.2f} Lots  |   -${sl_loss:.2f}   |   +${tp1_prof:.2f}      |   +${tp2_prof:.2f}")
                print("==================================================")

                if rr_tp2 < MIN_REQUIRED_RR:
                    print(f"   ❌ REJECTED [{symbol}]: R:R ({rr_tp2:.2f}R) is below minimum required {MIN_REQUIRED_RR}R. Skipping execution.")
                    decision = "WAIT"
                else:
                    print(f"   ✔ APPROVED [{symbol}]: High-asymmetry setup verified.")

                    risk_per_lot = risk_points * contract_size
                    if risk_per_lot > 0:
                        exact_lots = MAX_DOLLAR_RISK / risk_per_lot
                        recommended_lots = math.floor(exact_lots * 100) / 100
                        recommended_lots = max(0.01, recommended_lots)
                    else:
                        recommended_lots = 0.01

                    actual_dollar_risk = recommended_lots * risk_per_lot
                    print(f"   • Position Sizing: {recommended_lots} Lots (Actual Risk: ${actual_dollar_risk:.2f} | Max Allowed: ${MAX_DOLLAR_RISK:.2f})")

                print("==================================================")

                if decision in ["BUY", "SELL"]:
                    has_active_trade = False
                    if os.path.exists(TRADE_HISTORY_FILE):
                        df_check = pd.read_csv(TRADE_HISTORY_FILE)
                        if not df_check.empty and "status" in df_check.columns:
                            has_active_trade = not df_check[(df_check["status"] == "PENDING") & (df_check["symbol"] == symbol)].empty

                    if not has_active_trade:
                        trade_id = f"{symbol.replace('/', '')}_{now_ist.strftime('%Y%m%d_%H%M%S')}"
                        log_new_trade(trade_id, now_str, symbol, decision, planned_entry, planned_sl, planned_tp1, planned_tp2, recommended_lots)

                        # Build Multi-Lot Telegram Table
                        telegram_table_lines = []
                        for lot in [0.01, 0.02, 0.03, 0.05, 0.10]:
                            s_loss = lot * risk_points * contract_size
                            t1_prof = lot * reward_tp1 * contract_size
                            t2_prof = lot * reward_tp2 * contract_size
                            telegram_table_lines.append(f"`{lot:.2f}L | -${s_loss:.2f} | +${t1_prof:.2f} | +${t2_prof:.2f}`")
                        table_string = "\n".join(telegram_table_lines)

                        msg = (
                            f"🚨 *SMC TRADE SIGNAL FOR: {symbol} ({asset_name})* (`{trade_id}`)\n\n"
                            f"• *Active Trade:* `{symbol} - {asset_name}`\n"
                            f"• *Decision:* `{decision}`\n"
                            f"• *Current Live Price:* `{latest_price}`\n"
                            f"• *Target Entry Coordinate:* `{planned_entry}`\n"
                            f"• *Logical SL:* `{planned_sl}`\n"
                            f"• *Target 1 (EQ):* `{planned_tp1}`\n"
                            f"• *Target 2 (4H):* `{planned_tp2}`\n"
                            f"• *Recommended Lots:* `{recommended_lots}`\n"
                            f"• *Max Risk:* `${actual_dollar_risk:.2f}`\n"
                            f"• *Risk R:R:* `{rr_tp2:.2f}R`\n\n"
                            f"💰 *Multi-Lot Breakdown (Lot | SL | TP1 | TP2):*\n"
                            f"{table_string}\n\n"
                            f"• *Time (IST):* `{now_str}`"
                        )
                        send_telegram_alert(msg)
                    else:
                        print(f"   ⏳ [DUPLICATE BLOCKED] An active PENDING trade for {symbol} ({asset_name}) already exists. Skipping new entry.")

            except Exception as e:
                print(f"[{symbol}] Error fetching data: {e}")

            # API Rate-Limit Throttle: pause between tickers to stay safe under Twelve Data limits
            if idx < len(TICKERS) - 1:
                time.sleep(API_THROTTLE_SECONDS)

        time.sleep(SCAN_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_scanner()