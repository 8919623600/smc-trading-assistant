import time
import os
import csv
import json
import requests
import pandas as pd
from datetime import datetime
from alpaca_trade_api.rest import REST, TimeFrame
from config import SYMBOLS, POLL_INTERVAL_SECONDS, APCA_API_KEY_ID, APCA_API_SECRET_KEY, APCA_API_BASE_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from smc_engine import AdvancedSMCEngine

ACTIVE_TRADES_FILE = "active_trades.json"
HISTORY_FILE = "trade_history.csv"

def init_files():
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Symbol", "Type", "Entry", "SL", "TP1", "TP2", "LotSize", "Outcome", "ExitPrice", "PnL_USD"])
    
    if not os.path.exists(ACTIVE_TRADES_FILE):
        with open(ACTIVE_TRADES_FILE, mode='w') as f:
            json.dump({}, f)

def load_active_trades():
    try:
        with open(ACTIVE_TRADES_FILE, mode='r') as f:
            return json.load(f)
    except:
        return {}

def save_active_trades(trades):
    with open(ACTIVE_TRADES_FILE, mode='w') as f:
        json.dump(trades, f, indent=4)

def log_trade_history(trade_data):
    with open(HISTORY_FILE, mode='a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
            trade_data["symbol"],
            trade_data["type"],
            trade_data["entry"],
            trade_data["sl"],
            trade_data["tp1"],
            trade_data["tp2"],
            trade_data["lot_size"],
            trade_data["outcome"],
            trade_data["exit_price"],
            trade_data["pnl_usd"]
        ])

def send_telegram_alert(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"⚠️ Telegram alert error: {e}")

def send_daily_pnl_summary(target_date_str):
    if not os.path.exists(HISTORY_FILE):
        return

    wins = 0
    losses = 0
    total_pnl = 0.0
    total_trades = 0

    try:
        with open(HISTORY_FILE, mode='r') as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if not row or len(row) < 11:
                    continue
                timestamp = row[0]
                trade_date = timestamp.split(' ')[0]
                
                if trade_date == target_date_str:
                    total_trades += 1
                    outcome = row[8]
                    pnl = float(row[10])
                    total_pnl += pnl
                    if "TP" in outcome or pnl > 0:
                        wins += 1
                    else:
                        losses += 1
    except Exception as e:
        print(f"⚠️ Error reading trade history for daily summary: {e}")
        return

    if total_trades == 0:
        return

    win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
    emoji = "🟢" if total_pnl >= 0 else "🔴"

    summary_msg = (
        f"📊 *DAILY TRADING RECAP ({target_date_str})* 📊\n\n"
        f"📁 *Total Trades:* `{total_trades}`\n"
        f"✅ *Wins:* `{wins}` | ❌ *Losses:* `{losses}`\n"
        f"📈 *Win Rate:* `{win_rate:.1f}%`\n"
        f"{emoji} *Net Daily PnL:* `${total_pnl:.2f}`"
    )
    send_telegram_alert(summary_msg)

class AlpacaDataFetcher:
    """Fetches multi-timeframe candle data from Alpaca API for the SMC engine"""
    def __init__(self, api_client):
        self.api = api_client

    def get_market_data(self, symbol):
        data_dict = {}
        tf_mapping = {
            "1M": TimeFrame.Minute,
            "5M": TimeFrame(5, TimeFrame.Minute),
            "15M": TimeFrame(15, TimeFrame.Minute),
            "1H": TimeFrame.Hour
        }
        
        for tf_name, alpaca_tf in tf_mapping.items():
            try:
                bars = self.api.get_bars(symbol, alpaca_tf, limit=200).df
                if not bars.empty:
                    # Reset index to make timestamp a column
                    bars = bars.reset_index()
                    # Standardize column names for the SMC engine
                    bars = bars.rename(columns={'timestamp': 'timestamp', 'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close', 'volume': 'volume'})
                    data_dict[tf_name] = bars[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
                else:
                    data_dict[tf_name] = None
            except Exception as e:
                print(f"⚠️ Error fetching {tf_name} data for {symbol}: {e}")
                data_dict[tf_name] = None
                
        return data_dict

def check_active_trades(api, symbol, current_price, high_price, low_price):
    active_trades = load_active_trades()
    if symbol not in active_trades:
        return

    trade = active_trades[symbol]
    t_type = trade["type"]
    entry = trade["entry"]
    sl = trade["sl"]
    tp1 = trade["tp1"]
    tp2 = trade["tp2"]
    risk_usd = trade["risk_usd"]

    outcome = None
    exit_price = current_price
    pnl = 0.0

    if t_type == "BUY":
        if low_price <= sl:
            outcome = "SL_HIT"
            exit_price = sl
            pnl = -risk_usd
        elif high_price >= tp2:
            outcome = "TP2_HIT"
            exit_price = tp2
            pnl = risk_usd * 3.0
        elif high_price >= tp1 and not trade.get("tp1_hit", False):
            trade["tp1_hit"] = True
            save_active_trades(active_trades)
            send_telegram_alert(f"🎯 *TAKE PROFIT 1 HIT!* 📌 Asset: `{symbol}` | Price: `{tp1}`")

    elif t_type == "SELL":
        if high_price >= sl:
            outcome = "SL_HIT"
            exit_price = sl
            pnl = -risk_usd
        elif low_price <= tp2:
            outcome = "TP2_HIT"
            exit_price = tp2
            pnl = risk_usd * 3.0
        elif low_price <= tp1 and not trade.get("tp1_hit", False):
            trade["tp1_hit"] = True
            save_active_trades(active_trades)
            send_telegram_alert(f"🎯 *TAKE PROFIT 1 HIT!* 📌 Asset: `{symbol}` | Price: `{tp1}`")

    if outcome in ["SL_HIT", "TP2_HIT"]:
        trade["outcome"] = outcome
        trade["exit_price"] = exit_price
        trade["pnl_usd"] = pnl
        
        log_trade_history(trade)

        emoji = "✅" if "TP" in outcome else "❌"
        alert_msg = (
            f"{emoji} *ALPACA PAPER TRADE CLOSED: {outcome}* {emoji}\n\n"
            f"📌 *Asset:* `{symbol}`\n"
            f"⚡ *Type:* `{t_type}`\n"
            f"💵 *Entry:* `{entry}` | *Exit:* `{exit_price}`\n"
            f"💰 *Realized PnL:* `${pnl:.2f}`"
        )
        send_telegram_alert(alert_msg)

        del active_trades[symbol]
        save_active_trades(active_trades)

def run_bot():
    init_files()
    
    print("==================================================")
    print("🔗 SYSTEM CONNECTION HEALTH CHECK")
    print("==================================================")
    
    # 1. Check Telegram Connection
    telegram_status = "ACTIVE [ ✅ Verified ]" if TELEGRAM_BOT_TOKEN else "FAILED [ ❌ Missing Token ]"
    print(f"   🔹 Telegram Bot API Connection : {telegram_status}")

    # 2. Initialize Alpaca API Client
    try:
        api = REST(APCA_API_KEY_ID, APCA_API_SECRET_KEY, base_url=APCA_API_BASE_URL)
        account = api.get_account()
        print(f"   🔹 Alpaca Connection Status    : ACTIVE [ Portfolio Value: ${float(account.portfolio_value):.2f} ]")
    except Exception as e:
        print(f"   🔹 Alpaca Connection Status    : FAILED [ ❌ Error: {e} ]")

    # 3. Check Data Feed Connection
    fetcher = AlpacaDataFetcher(api)
    print(f"   🔹 Market Data Feed (Alpaca)   : ACTIVE [ ✅ Ready ]")
    
    print("==================================================")
    print("🤖 STARTING ALPACA AUTOMATED SMC PAPER BOT")
    print(f"📊 Monitored Assets: {SYMBOLS}")
    print("==================================================")

    send_telegram_alert("🚀 *Alpaca Automated SMC Paper Bot Online & Ready!*")

    engine = AdvancedSMCEngine(min_rr=1.5, max_rr=5.0)
    current_utc_date = datetime.utcnow().strftime('%Y-%m-%d')

    while True:
        try:
            now_utc = datetime.utcnow()
            today_str = now_utc.strftime('%Y-%m-%d')

            if today_str != current_utc_date:
                send_daily_pnl_summary(current_utc_date)
                current_utc_date = today_str

            print(f"\n==================================================")
            print(f"🕒 SCAN CYCLE: {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print(f"==================================================")

            for symbol in SYMBOLS:
                data_dict = fetcher.get_market_data(symbol)
                
                if data_dict.get("1M") is None or data_dict["1M"].empty:
                    print(f"⚠️ [{symbol}] Market Data Feed Error: No 1M data received.")
                    continue

                df_1m = data_dict["1M"]
                current_price = float(df_1m.iloc[-1]["close"])
                high_price = float(df_1m.iloc[-1]["high"])
                low_price = float(df_1m.iloc[-1]["low"])

                check_active_trades(api, symbol, current_price, high_price, low_price)

                signal = engine.analyze(data_dict, symbol=symbol)
                decision = signal["decision"]
                reason = signal["reason"]

                print(f"📈 Asset Chart: {symbol} | Current Price: {current_price}")
                print(f"🔍 Engine Decision: {decision} | Reason: {reason}")

                active_trades = load_active_trades()

                if decision in ["BUY", "SELL"] and symbol not in active_trades:
                    params = signal["trade_params"]
                    entry = params["entry"]
                    sl = params["sl"]
                    tp1 = params["tp1"]
                    tp2 = params["tp2"]

                    qty = 50.0  # <--- Updated quantity to 50
                    calculated_risk = abs(entry - sl) * qty

                    print(f"   🎯 NEW SMC LIMIT SETUP DETECTED:")
                    print(f"      • Limit Entry Target : {entry} (Waiting for pullback)")
                    print(f"      • Stop Loss          : {sl}")
                    print(f"      • Take Profit 1      : {tp1}")
                    print(f"      • Take Profit 2      : {tp2}")
                    
                    try:
                        # Submit a LIMIT order so it waits for the SMC pullback level
                        order = api.submit_order(
                            symbol=symbol,
                            qty=qty,
                            side=decision.lower(),
                            type='limit',
                            limit_price=entry,
                            time_in_force='gtc'
                        )
                        ticket_id = order.id
                        success = True
                        print(f"✅ Alpaca Limit Order Placed! Ticket ID: {ticket_id}")
                    except Exception as e:
                        print(f"❌ Order submission error: {e}")
                        success = False
                        ticket_id = None

                    if success:
                        active_trades[symbol] = {
                            "symbol": symbol,
                            "type": decision,
                            "entry": entry,
                            "sl": sl,
                            "tp1": tp1,
                            "tp2": tp2,
                            "lot_size": qty,
                            "risk_usd": calculated_risk,
                            "ticket": ticket_id,
                            "tp1_hit": False
                        }
                        save_active_trades(active_trades)

                        alert_msg = (
                            f"🤖 *ALPACA SMC LIMIT ORDER PLACED ({decision})* 🤖\n\n"
                            f"📌 *Asset:* `{symbol}`\n"
                            f"🎫 *Alpaca Order ID:* `{ticket_id}`\n"
                            f"📊 *Limit Entry:* `{entry}` | *Qty:* `{qty}`\n"
                            f"🛑 *SL:* `{sl}`\n"
                            f"🎯 *TP1:* `{tp1}` | 🎯 *TP2:* `{tp2}`\n"
                            f"📝 *Reason:* {reason}"
                        )
                        send_telegram_alert(alert_msg)

                elif symbol in active_trades:
                    print(f"   ⏳ Status: Trade active. Managing SL/TP targets...")
                else:
                    print(f"   ⏳ Status: Market consolidating. Awaiting structure.")

                print("-" * 50)

        except KeyboardInterrupt:
            print("\n🛑 Bot stopped manually by user.")
            send_telegram_alert("🛑 *Alpaca SMC Bot Stopped Manually.*")
            break
        except Exception as e:
            print(f"❌ Error in main execution loop: {e}")
            time.sleep(15)
            continue

        print(f"⏳ Waiting {POLL_INTERVAL_SECONDS} seconds for next candle scan...\n")
        time.sleep(POLL_INTERVAL_SECONDS)

if __name__ == "__main__":
    run_bot()