import time
import os
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
    print("🚀 SMC SIGNAL BOT ACTIVE (MULTI-STATE & ROTATION)")
    print(f"📊 Assets Monitored: {SYMBOLS}")
    print("==================================================")
    
    send_telegram_alert("🟢 *SMC Signal Bot Started & Scanning EUR/USD & XAU/USD*")

    fetcher = SmartRotatorFetcher(TWELVE_DATA_KEYS)
    engine = AdvancedSMCEngine(min_rr=2.0, max_rr=8.0)

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

                if status == "SETUP_FORMING":
                    msg = (
                        f"⏳ *SMC SETUP FORMING (Advance Notice)* ⏳\n\n"
                        f"📌 *Asset:* `{signal['symbol']}`\n"
                        f"⚡ *Anticipated Direction:* `{signal['direction']}`\n\n"
                        f"🔍 *Status:* Macro criteria & 1H liquidity sweep met. "
                        f"Now monitoring 1M candles for final entry trigger.\n\n"
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

                elif status == "TRIGGERED":
                    p = signal["trade_params"]
                    matrix_text = ""
                    for item in p["pnl_matrix"]:
                        matrix_text += (
                            f"• **{item['lot']} Lot**: "
                            f"Risk: -${item['loss']} | TP1: +${item['tp1']} | TP2: +${item['tp2']}\n"
                        )

                    msg = (
                        f"🚨 *SMC FINAL EXECUTION ALERT* 🚨\n\n"
                        f"📌 *Asset:* `{symbol}`\n"
                        f"⚡ *Direction:* `{signal['decision']}`\n\n"
                        f"🎯 *Entry:* `{p['entry']}`\n"
                        f"🛑 *Stop Loss:* `{p['sl']}` ({p['pips_risk']} Pips)\n"
                        f"🎯 *Take Profit 1:* `{p['tp1']}` (3R)\n"
                        f"🎯 *Take Profit 2:* `{p['tp2']}` (6R)\n"
                        f"⚖️ *Risk:Reward:* `{p['rr']}:1`\n\n"
                        f"📊 *LOT SIZE & PnL BREAKDOWN*\n"
                        f"{matrix_text}\n"
                        f"📝 *Confluence:* {signal['reason']}"
                    )
                    send_telegram_alert(msg)
                    print(f"🚨 Final Execution Alert Sent for {symbol}")

                else:
                    print(f"🔍 Asset: {symbol} | Status: HOLD | Reason: {signal.get('reason')}")

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