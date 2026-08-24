import time
import os
import csv
import requests
import pandas as pd
from datetime import datetime
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
    """Rotates between TWELVE_DATA_API_KEY_1 and TWELVE_DATA_API_KEY_2 to double rate limits"""
    def __init__(self, keys):
        self.keys = [k for k in keys if k]
        self.key_index = 0

    def get_next_client(self):
        if not self.keys:
            raise ValueError("No Twelve Data API keys provided!")
        active_key = self.keys[self.key_index]
        self.key_index = (self.key_index + 1) % len(self.keys)
        return TDClient(apikey=active_key)

    def get_market_data(self, symbol):
        data_dict = {}
        intervals = {"4H": "4h", "1H": "1h", "15M": "15min", "1M": "1min"}
        
        for tf_name, interval in intervals.items():
            try:
                client = self.get_next_client()
                time.sleep(7)
                
                ts = client.time_series(symbol=symbol, interval=interval, outputsize=100)
                df = ts.as_pandas()
                
                if df is not None and not df.empty:
                    df = df.reset_index()
                    if 'datetime' in df.columns:
                        df = df.rename(columns={'datetime': 'timestamp'})
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df = df.sort_values('timestamp').reset_index(drop=True)
                    data_dict[tf_name] = df
                else:
                    data_dict[tf_name] = None
            except Exception as e:
                print(f"⚠️ Error fetching {tf_name} for {symbol}: {e}")
                data_dict[tf_name] = None
        return data_dict

def run_bot():
    print("==================================================")
    print("🚀 SMC SIGNAL BOT ACTIVE (WITH AUDIT & CSV LOGGER)")
    print(f"📊 Assets Monitored: {SYMBOLS}")
    print("==================================================")
    
    send_telegram_alert("🟢 *SMC Signal Bot Started & Scanning EUR/USD & XAU/USD*")

    fetcher = SmartRotatorFetcher(TWELVE_DATA_KEYS)
    engine = AdvancedSMCEngine(min_rr=2.0, max_rr=8.0)
    
    # Tracks active live trades: {symbol: trade_dict}
    open_trades = {}

    while True:
        try:
            print(f"\n🕒 SCAN CYCLE START: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
            for symbol in SYMBOLS:
                data_dict = fetcher.get_market_data(symbol)
                
                if data_dict.get("1M") is None or data_dict.get("4H") is None:
                    print(f"⚠️ Skipping {symbol} due to incomplete data feed.")
                    continue

                signal = engine.analyze(data_dict, symbol)
                status = signal.get("status")

                if status == "LIQUIDITY_SWEPT" or "Sweep" in signal.get("reason", ""):
                    msg = (
                        f"🚨 *STEP 1: LIQUIDITY SWEEP DETECTED* 🚨\n\n"
                        f"📌 *Asset:* `{signal['symbol']}`\n"
                        f"⚡ *Direction Bias:* `{signal['direction']}`\n\n"
                        f"🔍 *Status:* External macro liquidity pool was just raided/swept. "
                        f"Now waiting for 15M structure confirmation (CHoCH / BOS).\n\n"
                        f"📝 *Details:* {signal['reason']}"
                    )
                    send_telegram_alert(msg)
                    print(f"🚨 Liquidity Sweep Alert Sent for {signal['symbol']}")

                elif status == "CHOCH_CONFIRMED":
                    p_fmt = f"{signal.get('poi_price', 0):.5f}" if "EUR" in symbol or "USD" in symbol else f"{signal.get('poi_price', 0):.2f}"
                    msg = (
                        f"⏳ *STEP 2: 15M CHoCH & FVG CONFIRMED* ⏳\n\n"
                        f"📌 *Asset:* `{signal['symbol']}`\n"
                        f"⚡ *Direction:* `{signal['direction']}`\n\n"
                        f"🔍 *Status:* Institutional structure shift confirmed. "
                        f"**Bot is now actively watching the 1M chart for an entry retracement into POI:** `{p_fmt}`\n\n"
                        f"📝 *Confluence:* {signal['reason']}"
                    )
                    send_telegram_alert(msg)
                    print(f"⏳ 15M CHoCH Alert Sent for {signal['symbol']} at POI {p_fmt}")

                elif status == "SETUP_FORMING":
                    p_fmt = f"{signal.get('poi_price', 0):.5f}" if "EUR" in symbol or "USD" in symbol else f"{signal.get('poi_price', 0):.2f}"
                    msg = (
                        f"⏳ *SMC SETUP FORMING (Advance Notice)* ⏳\n\n"
                        f"📌 *Asset:* `{signal['symbol']}`\n"
                        f"⚡ *Anticipated Direction:* `{signal['direction']}`\n\n"
                        f"🔍 *Status:* Macro criteria met. "
                        f"**Monitoring 1M chart for entry at POI:** `{p_fmt}`\n\n"
                        f"📝 *Confluence:* {signal['reason']}"
                    )
                    send_telegram_alert(msg)
                    print(f"⏳ Setup Forming Alert Sent for {signal['symbol']}")

                elif status == "INVALIDATED":
                    msg = (
                        f"❌ *SMC SETUP INVALIDATED* ❌\n\n"
                        f"📌 *Asset:* `{signal['symbol']}`\n"
                        f"⚠️ *Reason:* {signal['reason']}\n\n"
                        f"🛑 *Action:* Discarding previous setup watch."
                    )
                    send_telegram_alert(msg)
                    print(f"❌ Setup Invalidated Alert Sent for {signal['symbol']}")

                elif (status == "TRIGGERED" or "TRIGGER" in str(status) or "ENTRY" in str(status)) and symbol not in open_trades:
                    p = signal["trade_params"]
                    direction = signal["decision"]
                    
                    open_trades[symbol] = {
                        "direction": direction,
                        "entry": p["entry"],
                        "sl": p["sl"],
                        "tp1": p["tp1"],
                        "tp2": p["tp2"],
                        "tp3": p["tp3"],
                        "hit_tp1": False,
                        "hit_tp2": False
                    }

                    log_trade_event(
                        symbol, "ENTRY", p["entry"], p["sl"], 
                        p["tp1"], p["tp2"], p["tp3"], f"Direction: {direction} | RR: {p['rr']}"
                    )

                    matrix_text = ""
                    for item in p["pnl_matrix"]:
                        matrix_text += (
                            f"• **{item['lot']} Lot**: "
                            f"Risk: -${item['loss']} | TP1: +${item['tp1']} | TP2: +${item['tp2']}\n"
                        )

                    msg = (
                        f"🚨 *SMC FINAL EXECUTION ALERT* 🚨\n\n"
                        f"📌 *Asset:* `{symbol}`\n"
                        f"⚡ *Direction:* `{direction}`\n\n"
                        f"🎯 *Entry:* `{p['entry']}`\n"
                        f"🛑 *Stop Loss:* `{p['sl']}` ({p['pips_risk']} Pips)\n"
                        f"🎯 *Take Profit 1:* `{p['tp1']}`\n"
                        f"🎯 *Take Profit 2:* `{p['tp2']}`\n"
                        f"🎯 *Take Profit 3:* `{p['tp3']}`\n"
                        f"⚖️ *Risk:Reward:* `{p['rr']}:1`\n\n"
                        f"📊 *LOT SIZE & PnL BREAKDOWN*\n"
                        f"{matrix_text}\n"
                        f"📝 *Confluence:* {signal['reason']}"
                    )
                    send_telegram_alert(msg)
                    print(f"🚨 Final Execution Alert Sent & Logged for {symbol}")

                else:
                    print(f"🔍 Asset: {symbol} | Status: HOLD | Reason: {signal.get('reason')}")

                # --- ACTIVE TRADE AUDITING FOR TP / SL EXITS ---
                if symbol in open_trades:
                    trade = open_trades[symbol]
                    current_price = float(data_dict["1M"].iloc[-1]['close'])
                    
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

                    elif trade["direction"] == "SELL":
                        if current_price >= sl:
                            log_trade_event(symbol, "SL_HIT", entry, sl, tp1, tp2, tp3, f"Exit Price: {current_price}")
                            send_telegram_alert(f"❌ *STOP LOSS HIT* for `{symbol}` at `{current_price}`. Trade closed.")
                            print(f"❌ STOP LOSS HIT for {symbol} at {current_price}.")
                            del open_trades[symbol]
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