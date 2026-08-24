import time
import os
import csv
import requests
import pandas as pd
from datetime import datetime, time as dtime
from twelvedata import TDClient
from config import SYMBOLS, POLL_INTERVAL_SECONDS, TWELVE_DATA_KEYS, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from smc_engine import AdvancedSMCEngine

def send_telegram_alert(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"Telegram Output:\n{message}")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"⚠️ Telegram error: {e}")

# --- CSV TRADE HISTORY LOGGER ---
def log_trade_event(symbol, event_type, entry, sl, tp1, tp2, tp3, details):
    file_exists = os.path.isfile('trade_history.csv')
    try:
        with open('trade_history.csv', mode='a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['Timestamp', 'Symbol', 'Event', 'Entry', 'SL', 'TP1', 'TP2', 'TP3', 'Details'])
            timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            writer.writerow([timestamp, symbol, event_type, entry, sl, tp1, tp2, tp3, details])
    except Exception as e:
        print(f"⚠️ Error writing to trade_history.csv: {e}")

class SmartRotatorFetcher:
    """Rotates across Twelve Data API keys and automatically skips exhausted/failed keys"""
    def __init__(self, keys):
        self.keys = [k for k in keys if k]
        self.key_index = 0
        print(f"🔑 Loaded {len(self.keys)} API Key(s) into rotator.")

    def get_next_client(self):
        if not self.keys:
            raise ValueError("No Twelve Data API keys provided! Check your config or environment variables.")
        
        active_key = self.keys[self.key_index]
        masked_key = f"{active_key[:4]}...{active_key[-4:]}" if len(active_key) > 8 else "****"
        print(f"🔄 Rotating to API Key Index [{self.key_index + 1}/{len(self.keys)}] (Key: {masked_key})")
        
        # Advance index for the next request
        self.key_index = (self.key_index + 1) % len(self.keys)
        return TDClient(apikey=active_key)

    def fetch_single_series(self, symbol, interval):
        # Try through available keys until one succeeds or all fail
        for _ in range(len(self.keys)):
            try:
                client = self.get_next_client()
                time.sleep(2)  # Pacing
                ts = client.time_series(symbol=symbol, interval=interval, outputsize=100)
                df = ts.as_pandas()
                if df is not None and not df.empty:
                    df = df.reset_index()
                    if 'datetime' in df.columns:
                        df = df.rename(columns={'datetime': 'timestamp'})
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df = df.sort_values('timestamp').reset_index(drop=True)
                    return df
            except Exception as e:
                print(f"⚠️ Key hit limit or error fetching {interval} for {symbol}: {e}. Switching to next key...")
                continue
        print(f"❌ All available API keys failed or exhausted limits for {symbol} ({interval})")
        return None

def is_within_trading_window(symbol):
    now_utc = datetime.utcnow().time()
    
    # EUR/USD Windows: 1:30 PM - 4:30 PM UTC AND 7:00 PM - 1:30 AM UTC
    if "EUR" in symbol:
        session1 = dtime(13, 30) <= now_utc <= dtime(16, 30)
        session2 = dtime(19, 0) <= now_utc or now_utc <= dtime(1, 30)
        return session1 or session2
    
    # XAU/USD Windows: 7:00 PM - 1:30 AM UTC
    elif "XAU" in symbol:
        return dtime(19, 0) <= now_utc or now_utc <= dtime(1, 30)
        
    return True

def run_bot():
    print("==================================================")
    print("🚀 SMC SIGNAL BOT ACTIVE (SMART KEY FAILOVER & TIME WINDOWS)")
    print(f"📊 Assets Monitored: {SYMBOLS}")
    print(f"🔑 Configured Keys Array Length: {len(TWELVE_DATA_KEYS)}")
    print("==================================================")
    
    send_telegram_alert("🟢 *SMC Signal Bot Started with Smart Key Failover Active*")

    fetcher = SmartRotatorFetcher(TWELVE_DATA_KEYS)
    engine = AdvancedSMCEngine(min_rr=2.0, max_rr=8.0)
    
    open_trades = {}
    asset_states = {}
    
    # Caching dictionaries for higher timeframes (4H and 1H)
    htf_cache = {symbol: {"4H": None, "1H": None, "last_fetched": None} for symbol in SYMBOLS}

    while True:
        try:
            print(f"\n🕒 SCAN CYCLE START: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
            current_time = datetime.utcnow()

            for symbol in SYMBOLS:
                # Check trading session timing window
                if not is_within_trading_window(symbol):
                    print(f"💤 Asset: {symbol} | Outside active trading window. Skipping scan.")
                    continue

                # --- SMART CACHING FOR 4H & 1H (Fetch once every hour) ---
                cache = htf_cache[symbol]
                hour_elapsed = cache["last_fetched"] is None or (current_time - cache["last_fetched"]).total_seconds() >= 3600

                if hour_elapsed:
                    print(f"🔄 Refreshing cached 4H & 1H data for {symbol}...")
                    cache["4H"] = fetcher.fetch_single_series(symbol, "4h")
                    cache["1H"] = fetcher.fetch_single_series(symbol, "1h")
                    cache["last_fetched"] = current_time

                # Always fetch fast execution timeframes (15M and 1M) fresh every cycle
                df_15m = fetcher.fetch_single_series(symbol, "15min")
                df_1m = fetcher.fetch_single_series(symbol, "1min")

                data_dict = {
                    "4H": cache["4H"],
                    "1H": cache["1H"],
                    "15M": df_15m,
                    "1M": df_1m
                }
                
                if data_dict.get("1M") is None or data_dict.get("4H") is None or data_dict.get("1H") is None or data_dict.get("15M") is None:
                    print(f"⚠️ Skipping {symbol} due to incomplete data feed.")
                    continue

                signal = engine.analyze(data_dict, symbol)
                status = signal.get("status")
                reason = signal.get("reason", "")
                
                current_price = float(data_dict["1M"].iloc[-1]['close'])

                if symbol not in asset_states:
                    asset_states[symbol] = "IDLE"

                # 1. LIQUIDITY SWEEP CHECK (STEP 1)
                if status == "LIQUIDITY_SWEPT":
                    low_val, high_val = "N/A", "N/A"
                    if "Lows:" in reason and "Highs:" in reason:
                        try:
                            parts = reason.split("[")
                            levels_part = parts[1].replace("]", "").split("|")
                            low_val = levels_part[0].replace("Lows:", "").strip()
                            high_val = levels_part[1].replace("Highs:", "").strip()
                            sweep_display = f"Lows: {low_val} | Highs: {high_val}"
                        except:
                            sweep_display = "External Range Boundary"
                    else:
                        sweep_display = reason

                    direction_bias = signal.get('direction', 'SELL')
                    if direction_bias == "SELL":
                        liquidity_type = f"Sell-Side Liquidity Swept (Below Low: {low_val}) -> Expecting Bearish CHoCH reversal"
                    else:
                        liquidity_type = f"Buy-Side Liquidity Swept (Above High: {high_val}) -> Expecting Bullish CHoCH reversal"

                    if asset_states[symbol] != "SWEEP_ALERTED":
                        asset_states[symbol] = "SWEEP_ALERTED"
                        msg = (
                            f"🚨 *STEP 1: LIQUIDITY SWEEP DETECTED* 🚨\n\n"
                            f"📌 *Asset:* `{symbol}`\n"
                            f"⚡ *Direction Bias:* `{direction_bias}`\n\n"
                            f"📍 *Swept Levels:* `{sweep_display}`\n"
                            f"💧 *Liquidity Type:* `{liquidity_type}`\n"
                            f"🔍 *Looking for CHoCH at:* Awaiting 15M structure break past boundary levels."
                        )
                        send_telegram_alert(msg)
                        print(f"🚨 Liquidity Sweep Alert Sent for {symbol}")
                    
                    print(f"🔍 Asset: {symbol} | Status: HOLD | Reason: {reason}")

                # 2. CHoCH CONFIRMED CHECK (STEP 2)
                elif status == "CHOCH_CONFIRMED":
                    choch_lvl = signal.get("choch_price", signal.get("level", 0))
                    c_fmt = f"{choch_lvl:.5f}" if "EUR" in symbol or "USD" in symbol else f"{choch_lvl:.2f}"
                    p_fmt = f"{signal.get('poi_price', 0):.5f}" if "EUR" in symbol or "USD" in symbol else f"{signal.get('poi_price', 0):.2f}"
                    
                    if asset_states[symbol] != "CHOCH_ALERTED":
                        asset_states[symbol] = "CHOCH_ALERTED"
                        msg = (
                            f"⏳ *STEP 2: 15M CHoCH & FVG CONFIRMED* ⏳\n\n"
                            f"📌 *Asset:* `{symbol}`\n"
                            f"⚡ *Direction:* `{signal.get('direction', '')}`\n\n"
                            f"📍 *CHoCH Happened At:* `{c_fmt}`\n"
                            f"🎯 *Active Watch (POI):* `{p_fmt}`\n\n"
                            f"📝 *Confluence:* {reason}"
                        )
                        send_telegram_alert(msg)
                        print(f"⏳ 15M CHoCH Alert Sent for {symbol} at Level {c_fmt}")
                    
                    print(f"🔍 Asset: {symbol} | Status: HOLD | Reason: {reason}")

                # 3. SETUP FORMING CHECK
                elif status == "SETUP_FORMING":
                    p_fmt = f"{signal.get('poi_price', 0):.5f}" if "EUR" in symbol or "USD" in symbol else f"{signal.get('poi_price', 0):.2f}"
                    msg = (
                        f"⏳ *SMC SETUP FORMING (Advance Notice)* ⏳\n\n"
                        f"📌 *Asset:* `{symbol}`\n"
                        f"⚡ *Anticipated Direction:* `{signal.get('direction', '')}`\n\n"
                        f"🔍 *Status:* Macro criteria met. "
                        f"**Monitoring 1M chart for entry at POI:** `{p_fmt}`\n\n"
                        f"📝 *Confluence:* {reason}"
                    )
                    send_telegram_alert(msg)
                    print(f"⏳ Setup Forming Alert Sent for {symbol}")
                    print(f"🔍 Asset: {symbol} | Status: HOLD | Reason: {reason}")

                # 4. INVALIDATED CHECK
                elif status == "INVALIDATED":
                    if asset_states[symbol] != "INVALIDATED":
                        asset_states[symbol] = "IDLE"
                        msg = (
                            f"❌ *SMC SETUP INVALIDATED* ❌\n\n"
                            f"📌 *Asset:* `{symbol}`\n"
                            f"⚠️ *Reason:* {reason}\n\n"
                            f"🛑 *Action:* Discarding previous setup watch. Resetting to scan new liquidity sweeps."
                        )
                        send_telegram_alert(msg)
                        print(f"❌ Setup Invalidated Alert Sent for {symbol} - State Reset.")
                    
                    print(f"🔍 Asset: {symbol} | Status: HOLD | Reason: {reason}")

                # 5. TRIGGERED / EXECUTION CHECK (STEP 3)
                elif (status == "TRIGGERED" or "TRIGGER" in str(status) or "ENTRY" in str(status)) and symbol not in open_trades:
                    asset_states[symbol] = "IN_TRADE"
                    p = signal.get("trade_params", {})
                    direction = signal.get("decision", signal.get("direction", "BUY"))
                    
                    open_trades[symbol] = {
                        "direction": direction,
                        "entry": p.get("entry", 0),
                        "sl": p.get("sl", 0),
                        "tp1": p.get("tp1", 0),
                        "tp2": p.get("tp2", 0),
                        "tp3": p.get("tp3", 0),
                        "hit_tp1": False,
                        "hit_tp2": False
                    }

                    log_trade_event(
                        symbol, "ENTRY", p.get("entry", 0), p.get("sl", 0), 
                        p.get("tp1", 0), p.get("tp2", 0), p.get("tp3", 0), f"Direction: {direction} | RR: {p.get('rr', 0)}"
                    )

                    base_risk_unit = p.get("pips_risk", 10)
                    matrix_text = ""
                    target_lots = [0.01, 0.02, 0.03, 0.1, 0.2, 0.5, 1.0]
                    
                    engine_matrix = p.get("pnl_matrix", [])
                    if engine_matrix:
                        for item in engine_matrix:
                            matrix_text += (
                                f"• `{item.get('lot', 0)} Lot`: "
                                f"Risk: -${item.get('loss', 0):.2f} | TP1: +${item.get('tp1', 0):.2f} | TP2: +${item.get('tp2', 0):.2f}\n"
                            )
                    else:
                        for lot in target_lots:
                            loss_est = lot * base_risk_unit * 10
                            tp1_est = loss_est * 1.5
                            tp2_est = loss_est * 3.0
                            matrix_text += (
                                f"• `{lot} Lot`: "
                                f"Risk: -${loss_est:.2f} | TP1: +${tp1_est:.2f} | TP2: +${tp2_est:.2f}\n"
                            )

                    msg = (
                        f"🚨 *STEP 3: SMC FINAL EXECUTION TRIGGER* 🚨\n\n"
                        f"📌 *Asset:* `{symbol}`\n"
                        f"⚡ *Direction:* `{direction}`\n\n"
                        f"🎯 *Entry Price:* `{p.get('entry', 0)}`\n"
                        f"🛑 *Stop Loss:* `{p.get('sl', 0)}`\n"
                        f"🎯 *Take Profit 1:* `{p.get('tp1', 0)}`\n"
                        f"🎯 *Take Profit 2:* `{p.get('tp2', 0)}`\n"
                        f"🎯 *Take Profit 3:* `{p.get('tp3', 0)}`\n"
                        f"⚖️ *Risk:Reward:* `{p.get('rr', 0)}:1`\n\n"
                        f"📊 *LOT SIZE PnL BREAKDOWN (0.01 to 1.0)*\n"
                        f"{matrix_text}\n"
                        f"📝 *Confluence:* {reason}"
                    )
                    send_telegram_alert(msg)
                    print(f"🚨 Final Execution Alert Sent & Logged for {symbol}")

                else:
                    if asset_states[symbol] not in ["SWEEP_ALERTED", "CHOCH_ALERTED", "IN_TRADE"]:
                        asset_states[symbol] = "IDLE"
                    print(f"🔍 Asset: {symbol} | Status: HOLD | Reason: {reason}")

                # --- ACTIVE TRADE AUDITING FOR TP / SL EXITS ---
                if symbol in open_trades:
                    trade = open_trades[symbol]
                    entry = trade["entry"]
                    sl = trade["sl"]
                    tp1 = trade["tp1"]
                    tp2 = trade["tp2"]
                    tp3 = trade["tp3"]

                    if trade["direction"] == "BUY":
                        if current_price <= sl:
                            log_trade_event(symbol, "SL_HIT", entry, sl, tp1, tp2, tp3, f"Exit Price: {current_price}")
                            send_telegram_alert(f"❌ *STOP LOSS HIT* for `{symbol}` at `{current_price}`. Trade closed.")
                            print(f"❌ STOP LOSS HIT for {symbol} at {current_price}.")
                            del open_trades[symbol]
                            asset_states[symbol] = "IDLE"
                        elif not trade["hit_tp1"] and current_price >= tp1:
                            trade["hit_tp1"] = True
                            log_trade_event(symbol, "TP1_HIT", entry, sl, tp1, tp2, tp3, f"Exit Price: {current_price}")
                            send_telegram_alert(f"🎯 *TP1 REACHED* for `{symbol}` at `{current_price}`!")
                            print(f"🎯 TP1 REACHED for {symbol} at {current_price}!")
                        elif not trade["hit_tp2"] and current_price >= tp2:
                            trade["hit_tp2"] = True
                            log_trade_event(symbol, "TP2_HIT", entry, sl, tp1, tp2, tp3, f"Exit Price: {current_price}")
                            send_telegram_alert(f"🎯 *TP2 REACHED* for `{symbol}` at `{current_price}`!")
                            print(f"🎯 TP2 REACHED for {symbol} at {current_price}!")
                        elif current_price >= tp3:
                            log_trade_event(symbol, "TP3_HIT_CLOSED", entry, sl, tp1, tp2, tp3, f"Exit Price: {current_price}")
                            send_telegram_alert(f"🏆 *TP3 FULL TARGET REACHED* for `{symbol}` at `{current_price}`! Trade fully closed.")
                            print(f"🏆 TP3 FULL TARGET HIT for {symbol} at {current_price}!")
                            del open_trades[symbol]
                            asset_states[symbol] = "IDLE"

                    elif trade["direction"] == "SELL":
                        if current_price >= sl:
                            log_trade_event(symbol, "SL_HIT", entry, sl, tp1, tp2, tp3, f"Exit Price: {current_price}")
                            send_telegram_alert(f"❌ *STOP LOSS HIT* for `{symbol}` at `{current_price}`. Trade closed.")
                            print(f"❌ STOP LOSS HIT for {symbol} at {current_price}.")
                            del open_trades[symbol]
                            asset_states[symbol] = "IDLE"
                        elif not trade["hit_tp1"] and current_price <= tp1:
                            trade["hit_tp1"] = True
                            log_trade_event(symbol, "TP1_HIT", entry, sl, tp1, tp2, tp3, f"Exit Price: {current_price}")
                            send_telegram_alert(f"🎯 *TP1 REACHED* for `{symbol}` at `{current_price}`!")
                            print(f"🎯 TP1 REACHED for {symbol} at {current_price}!")
                        elif not trade["hit_tp2"] and current_price <= tp2:
                            trade["hit_tp2"] = True
                            log_trade_event(symbol, "TP2_HIT", entry, sl, tp1, tp2, tp3, f"Exit Price: {current_price}")
                            send_telegram_alert(f"🎯 *TP2 REACHED* for `{symbol}` at `{current_price}`!")
                            print(f"🎯 TP2 REACHED for {symbol} at {current_price}!")
                        elif current_price <= tp3:
                            log_trade_event(symbol, "TP3_HIT_CLOSED", entry, sl, tp1, tp2, tp3, f"Exit Price: {current_price}")
                            send_telegram_alert(f"🏆 *TP3 FULL TARGET REACHED* for `{symbol}` at `{current_price}`! Trade fully closed.")
                            print(f"🏆 TP3 FULL TARGET HIT for {symbol} at {current_price}!")
                            del open_trades[symbol]
                            asset_states[symbol] = "IDLE"

            print("-" * 50)
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user.")
            send_telegram_alert("🛑 *SMC Signal Bot Stopped Manually.*")
            break
        except Exception as e:
            print(f"❌ Error in loop: {e}")
            time.sleep(20)
            continue

        time.sleep(POLL_INTERVAL_SECONDS)

if __name__ == "__main__":
    run_bot()