import os
import sys
import time
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# Ensure root directory is in sys.path so Python can find smc_engine.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Global IST Timezone Definition
IST = ZoneInfo("Asia/Kolkata")

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "YOUR_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID")
TICKER = "GC=F" # Gold Futures
TRADE_CSV_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../trade_history.csv'))

class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"

    def send_message(self, text: str):
        if not self.token or not self.chat_id or self.token == "YOUR_BOT_TOKEN":
            print("[Telegram] Credentials not configured. Skipping alert.")
            return False
            
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        try:
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"[Telegram Error] Failed to send alert: {e}")
            return False

def log_trade_to_csv(decision, params, bias_4h, bar_time):
    """Appends trade details to trade_history.csv for monthly reports."""
    file_exists = os.path.exists(TRADE_CSV_FILE)
    
    row_data = {
        "timestamp": bar_time,
        "action": decision,
        "asset": "Gold (XAU/USD)",
        "bias_4h": bias_4h,
        "entry": params.get("entry"),
        "sl": params.get("sl"),
        "tp1": params.get("tp1"),
        "tp2": params.get("tp2"),
        "rr": params.get("rr"),
        "status": "SIGNALED"
    }
    
    df_row = pd.DataFrame([row_data])
    try:
        if not file_exists:
            df_row.to_csv(TRADE_CSV_FILE, index=False)
        else:
            df_row.to_csv(TRADE_CSV_FILE, mode='a', header=False, index=False)
        print("📁 Trade details successfully recorded to trade_history.csv")
    except Exception as e:
        print(f"⚠️ Error logging trade to CSV: {e}")

from smc_engine import SMCTradingEngine

def fetch_live_data():
    """Fetches recent data frames to construct multi-timeframe inputs for the live engine."""
    try:
        df_1m = yf.download(TICKER, period="5d", interval="1m", progress=False)
        if df_1m.empty:
            return None
            
        if isinstance(df_1m.columns, pd.MultiIndex):
            df_1m.columns = [col[0] for col in df_1m.columns]
        df_1m.columns = [str(c).lower() for c in df_1m.columns]
        
        if 'datetime' not in df_1m.columns and 'date' in df_1m.columns:
            df_1m.rename(columns={'date': 'datetime'}, inplace=True)
        elif 'datetime' not in df_1m.columns:
            df_1m.reset_index(inplace=True)
            df_1m.rename(columns={df_1m.columns[0]: 'datetime'}, inplace=True)
            
        df_1m['datetime'] = pd.to_datetime(df_1m['datetime'], errors='coerce')
        df_1m = df_1m.dropna(subset=['datetime']).sort_values('datetime').reset_index(drop=True)
        
        # Resample higher timeframes dynamically
        df_temp = df_1m.set_index('datetime')
        df_15m = df_temp.resample('15min').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna().reset_index()
        df_1h = df_temp.resample('1h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna().reset_index()
        df_4h = df_temp.resample('4h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna().reset_index()
        
        return {
            "4H": df_4h,
            "1H": df_1h,
            "15M": df_15m,
            "1M": df_1m
        }
    except Exception as e:
        print(f"Data fetch error: {e}")
        return None

def main():
    print("==================================================")
    print("🤖 STARTING SMC LIVE STATE MACHINE BOT & TELEGRAM")
    print("==================================================")
    
    engine = SMCTradingEngine(min_rr=2.0, max_rr=8.0)
    notifier = TelegramNotifier(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    
    last_alerted_candle = None
    current_day = None
    trades_today = 0

    while True:
        try:
            now_ist = datetime.now(IST)
            time_str = now_ist.strftime('%Y-%m-%d %I:%M:%S %p IST')
            print(f"[{time_str}] Scanning market structure...")
            
            data_dict = fetch_live_data()
            if data_dict is None:
                time.sleep(60)
                continue
                
            df_1m = data_dict["1M"]
            current_bar = df_1m.iloc[-1]
            bar_time = current_bar['datetime']
            
            # Reset daily trade limits on date change
            if bar_time.date() != current_day:
                current_day = bar_time.date()
                trades_today = 0

            if bar_time == last_alerted_candle:
                time.sleep(30)
                continue

            # Max 2 trades per day cap check
            if trades_today >= 2:
                print("-> Daily trade cap (2 trades) reached. Skipping scan...")
                time.sleep(300)
                continue

            # Run full state machine evaluation
            analysis = engine.analyze(data_dict)
            decision = analysis.get("decision")
            reason = analysis.get("reason", "")

            print(f"-> Decision: {decision} | Reason: {reason}")

            if decision in ["BUY", "SELL"]:
                params = analysis.get("trade_params", {})
                if params:
                    last_alerted_candle = bar_time
                    trades_today += 1
                    
                    entry = params.get("entry")
                    sl = params.get("sl")
                    tp1 = params.get("tp1")
                    tp2 = params.get("tp2")
                    rr = params.get("rr")
                    bias_4h = analysis.get("bias_4h")
                    
                    # 1. Log trade details into CSV for monthly reviews
                    log_trade_to_csv(decision, params, bias_4h, bar_time)

                    # 2. Dispatch Telegram Alert
                    alert_text = (
                        f"🚨 *SMC INSTITUTIONAL SIGNAL* 🚨\n\n"
                        f"**Action:** `{decision}`\n"
                        f"**Asset:** Gold (XAU/USD)\n"
                        f"**4H Bias:** `{bias_4h}`\n"
                        f"**Entry Price:** `{entry}`\n"
                        f"**Stop Loss:** `{sl}`\n"
                        f"**Take Profit 1 (1.5R):** `{tp1}`\n"
                        f"**Take Profit 2 (Structural):** `{tp2}`\n"
                        f"**Risk/Reward:** `{rr}R`\n"
                        f"**Status:** Setup fully validated across state machine."
                    )
                    notifier.send_message(alert_text)
                    print("✅ Trade signal found, logged to CSV, and Telegram alert dispatched!")

        except KeyboardInterrupt:
            print("\nShutting down live bot safely.")
            break
        except Exception as e:
            print(f"⚠️ Loop exception: {e}")
            
        time.sleep(60)

if __name__ == "__main__":
    main()