import os
import sys
import time
import pandas as pd
import requests
import yfinance as yf

# --- ROBUST ABSOLUTE PATH SETUP ---
root_dir = "/home/ec2-user/trading/googleengine"
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from smc_engine import SMCTradingEngine

# --- CONFIGURATION & CREDENTIALS ---
SYMBOL = "GC=F"  # Gold Futures
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "YOUR_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID")
TRADE_CSV_FILE = os.path.join(root_dir, "trade_history.csv")

def send_telegram_alert(message):
    """Sends formatted alerts directly to your Telegram chat."""
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "YOUR_BOT_TOKEN":
        print("⚠️ Telegram token not configured. Skipping alert.")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if not response.json().get("ok"):
            print(f"⚠️ Telegram Error: {response.text}")
    except Exception as e:
        print(f"⚠️ Failed to send Telegram alert: {e}")

def fetch_market_data():
    """Fetches multi-timeframe data required for SMC analysis."""
    data_dict = {}
    try:
        # Fetching data across timeframes
        data_dict["4H"] = yf.download(SYMBOL, interval="60m", period="5d", progress=False) # Proxy/equivalent or actual
        data_dict["1M"] = yf.download(SYMBOL, interval="1m", period="1d", progress=False)
        
        # Clean up multi-index columns if yfinance returns them
        for tf in data_dict:
            df = data_dict[tf]
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            data_dict[tf] = df.dropna()
            
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error fetching market data: {e}")
        
    return data_dict

def log_trade_to_csv(trade_params, decision, reason):
    """Logs executed trades to CSV history file."""
    file_exists = os.path.isfile(TRADE_CSV_FILE)
    df_new = pd.DataFrame([{
        "timestamp": pd.Timestamp.now(),
        "decision": decision,
        "entry": trade_params.get("entry"),
        "sl": trade_params.get("sl"),
        "tp1": trade_params.get("tp1"),
        "tp2": trade_params.get("tp2"),
        "rr": trade_params.get("rr"),
        "reason": reason
    }])
    
    df_new.to_csv(TRADE_CSV_FILE, mode='a', index=False, header=not file_exists)

def main():
    print("==================================================")
    print("🤖 STARTING SMC LIVE STATE MACHINE BOT & TELEGRAM")
    print("==================================================")
    
    engine = SMCTradingEngine(min_rr=2.0, max_rr=8.0)
    last_signal_time = None

    while True:
        current_time_str = time.strftime('%Y-%m-%d %H:%M:%S IST')
        print(f"[{current_time_str}] Scanning market structure for {SYMBOL}...")
        
        data_dict = fetch_market_data()
        df_1m = data_dict.get("1M")
        
        if df_1m is not None and not df_1m.empty:
            current_price = float(df_1m.iloc[-1]['close'])
            print(f"-> Asset: Gold | Current Price: {current_price:.2f}")
            
            # Run SMC Engine analysis
            result = engine.analyze(data_dict)
            decision = result.get("decision")
            bias_4h = result.get("bias_4h")
            reason = result.get("reason")
            trade_params = result.get("trade_params", {})
            
            print(f"-> Decision: {decision or 'None'} | Bias: {bias_4h} | Reason: {reason}")
            
            # If a valid BUY/SELL signal is triggered
            if decision in ["BUY", "SELL"]:
                signal_signature = f"{decision}_{trade_params.get('entry')}"
                
                # Prevent spamming duplicate signals on consecutive candles
                if last_signal_time != signal_signature:
                    last_signal_time = signal_signature
                    
                    # Log trade
                    log_trade_to_csv(trade_params, decision, reason)
                    
                    # Format Telegram Alert Card
                    alert_message = (
                        f"🚨 *SMC LIVE TRADE SIGNAL* 🚨\n\n"
                        f"*Asset:* Gold (`{SYMBOL}`) / 1M Execution\n"
                        f"*Decision:* {'🟢 **BUY**' if decision == 'BUY' else '🔴 **SELL**'}\n"
                        f"*4H Bias:* {bias_4h} 📈\n\n"
                        f"*Trade Parameters:*\n"
                        f"• *Entry Price:* `{trade_params.get('entry')}`\n"
                        f"• *Stop Loss (SL):* `{trade_params.get('sl')}`\n"
                        f"• *Take Profit 1 (TP1):* `{trade_params.get('tp1')}`\n"
                        f"• *Take Profit 2 (TP2):* `{trade_params.get('tp2')}`\n"
                        f"• *Risk/Reward (R:R):* `{trade_params.get('rr')}`\n\n"
                        f"*Reasoning:*\n{reason}\n\n"
                        f"⏱ *Timestamp:* `{current_time_str}`"
                    )
                    
                    send_telegram_alert(alert_message)
                    print(f"✅ Executed and pushed {decision} signal alert to Telegram!")
        else:
            print("-> Warning: Failed to retrieve valid 1M market candles. Retrying...")

        # Wait 60 seconds before next scan loop
        time.sleep(60)

if __name__ == "__main__":
    main()