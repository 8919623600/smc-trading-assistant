import time
import os
import csv
import requests
import pandas as pd
from datetime import datetime, time as dtime, timedelta
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
    """Rotates across Twelve Data API keys and silently skips exhausted/failed keys"""
    def __init__(self, keys):
        self.keys = [k for k in keys if k]
        self.key_index = 0
        print(f"🔑 Loaded {len(self.keys)} API Key(s) into rotator.")

    def fetch_single_series(self, symbol, interval):
        if not self.keys:
            raise ValueError("No Twelve Data API keys provided! Check your config or environment variables.")

        attempts = len(self.keys)
        for _ in range(attempts):
            active_key = self.keys[self.key_index]
            
            try:
                time.sleep(2)  # Pacing
                client = TDClient(apikey=active_key)
                ts = client.time_series(symbol=symbol, interval=interval, outputsize=100)
                df = ts.as_pandas()
                
                if df is not None and not df.empty:
                    self.key_index = (self.key_index + 1) % len(self.keys)
                    df = df.reset_index()
                    if 'datetime' in df.columns:
                        df = df.rename(columns={'datetime': 'timestamp'})
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df = df.sort_values('timestamp').reset_index(drop=True)
                    return df
            except Exception:
                self.key_index = (self.key_index + 1) % len(self.keys)
                continue
                
        print(f"❌ All available API keys failed or exhausted limits for {symbol} ({interval})")
        return None

def is_within_trading_window(symbol):
    now_utc = datetime.utcnow()
    now_ist = (now_utc + timedelta(hours=5, minutes=30)).time()
    
    if "EUR" in symbol:
        return True
    elif "XAU" in symbol:
        return dtime(19, 0) <= now_ist or now_ist <= dtime(0, 30)
    return True

def run_bot():
    print("==================================================")
    print("🚀 SMC SIGNAL BOT ACTIVE (SILENT FAILOVER & IST WINDOWS)")
    print(f"📊 Assets Monitored: {SYMBOLS}")
    print(f"🔑 Configured Keys Array Length: {len(TWELVE_DATA_KEYS)}")
    print("==================================================")
    
    send_telegram_alert("🟢 *SMC Signal Bot Started with Silent Key Failover Active*")

    fetcher = SmartRotatorFetcher(TWELVE_DATA_KEYS)
    engine = AdvancedSMCEngine(min_rr=2.0, max_rr=8.0)
    
    open_trades = {}
    asset_states = {}
    
    htf_cache = {symbol: {"4H": None, "1H": None, "last_fetched": None} for symbol in SYMBOLS}

    while True:
        try:
            print(f"\n🕒 SCAN CYCLE START: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
            current_time = datetime.utcnow()

            for symbol in SYMBOLS:
                if not is_within_trading_window(symbol):
                    print(f"💤 Asset: {symbol} | Outside active trading window. Skipping scan.")
                    continue

                cache = htf_cache[symbol]
                hour_elapsed = cache["last_fetched"] is None or (current_time - cache["last_fetched"]).total_seconds() >= 3600

                if hour_elapsed:
                    print(f"🔄 Refreshing cached 4H & 1H data for {symbol}...")
                    cache["4H"] = fetcher.fetch_single_series(symbol, "4h")
                    cache["1H"] = fetcher.fetch_single_series(symbol, "1h")
                    cache["last_fetched"] = current_time

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
                if status == "LIQUIDITY_SWEPT" or "Sweep" in reason:
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

                    direction_bias = signal.get('direction', 'BUY')
                    if direction_bias == "SELL" or "SELL" in reason:
                        direction_bias = "SELL"
                        liquidity_type = f"Sell-Side Liquidity Swept (Below Low: {low_val}) -> Expecting Bearish CHoCH reversal"
                    else:
                        direction_bias = "BUY"
                        liquidity_type = f"Buy-Side Liquidity Swept (Above High: {high_val}) -> Expecting Bullish CHoCH reversal"

                    if asset_states.get(symbol) != "SWEEP_ALERTED":
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

                # 2. CHoCH / BOS CONFIRMED CHECK (STEP 2)
                elif status == "CHOCH_CONFIRMED" or "CHOCH" in reason or "BOS" in reason:
                    choch_lvl = signal.get("choch_price", 0)
                    poi_lvl = signal.get("poi_price", 0)
                    
                    c_fmt = f"{choch_lvl:.5f}" if "EUR" in symbol or "USD" in symbol else f"{choch_lvl:.2f}"
                    p_fmt = f"{poi_lvl:.5f}" if "EUR" in symbol or "USD" in symbol else f"{poi_lvl:.2f}"
                    
                    if asset_states.get(symbol) != "CHOCH_ALERTED":
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

                # 3. INVALIDATED CHECK
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

                # 4. TRIGGERED / EXECUTION CHECK (STEP 3)
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
                        elif not trade["hit_tp2"] and current_price >= tp2:
                            trade["hit_tp2"] = True
                            log_trade_event(symbol, "TP2_HIT", entry, sl, tp1, tp2, tp3, f"Exit Price: {current_price}")
                            send_telegram_alert(f"🎯 *TP2 REACHED* for `{symbol}` at `{current_price}`!")
                        elif current_price >= tp3:
                            log_trade_event(symbol, "TP3_HIT_CLOSED", entry, sl, tp1, tp2, tp3, f"Exit Price: {current_price}")
                            send_telegram_alert(f"🏆 *TP3 FULL TARGET REACHED* for `{symbol}` at `{current_price}`! Trade fully closed.")
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
                        elif not trade["hit_tp2"] and current_price <= tp2:
                            trade["hit_tp2"] = True
                            log_trade_event(symbol, "TP2_HIT", entry, sl, tp1, tp2, tp3, f"Exit Price: {current_price}")
                            send_telegram_alert(f"🎯 *TP2 REACHED* for `{symbol}` at `{current_price}`!")
                        elif current_price <= tp3:
                            log_trade_event(symbol, "TP3_HIT_CLOSED", entry, sl, tp1, tp2, tp3, f"Exit Price: {current_price}")
                            send_telegram_alert(f"🏆 *TP3 FULL TARGET REACHED* for `{symbol}` at `{current_price}`! Trade fully closed.")
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