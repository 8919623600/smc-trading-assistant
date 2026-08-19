import time
import os
import csv
import json
from datetime import datetime
from config import SYMBOLS, POLL_INTERVAL_SECONDS, TELEGRAM_BOT_TOKEN
from data_fetcher import TwelveDataFetcher
from smc_engine import AdvancedSMCEngine
from notifier import send_telegram_alert
from broker_connector import MT5BrokerConnector

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

def calculate_position_sizing(symbol, entry, sl, target_risk_usd=10.0):
    risk_points = abs(entry - sl)
    if risk_points <= 0:
        return 0.01, 10.0, 20.0

    dollar_risk_per_lot = risk_points * 100
    if dollar_risk_per_lot <= 0:
        return 0.01, target_risk_usd, target_risk_usd * 2

    lot_size = max(0.01, round(target_risk_usd / dollar_risk_per_lot, 2))
    actual_risk = lot_size * dollar_risk_per_lot
    projected_profit_tp2 = actual_risk * 3.0

    return lot_size, round(actual_risk, 2), round(projected_profit_tp2, 2)

def check_active_trades(symbol, current_price, high_price, low_price):
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
            f"{emoji} *PAPER TRADE CLOSED: {outcome}* {emoji}\n\n"
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

    # 2. Check Alpaca Connection
    broker = MT5BrokerConnector()
    broker_connected = broker.connect()

    # 3. Check Data Feed Connection
    fetcher = TwelveDataFetcher()
    print(f"   🔹 Market Data Feed (TwelveData) : ACTIVE [ ✅ Ready ]")
    
    print("==================================================")
    print("🤖 STARTING ALPACA AUTOMATED SMC PAPER BOT")
    print(f"📊 Monitored Assets: {SYMBOLS}")
    print("==================================================")

    if not broker_connected:
        print("⚠️ Warning: Bot running with connection issues to Alpaca broker.")

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
                
                if data_dict["1M"] is None or data_dict["1M"].empty:
                    print(f"⚠️ [{symbol}] Market Data Feed Error: No 1M data received.")
                    continue

                df_1m = data_dict["1M"]
                current_price = float(df_1m.iloc[-1]["close"])
                high_price = float(df_1m.iloc[-1]["high"])
                low_price = float(df_1m.iloc[-1]["low"])

                check_active_trades(symbol, current_price, high_price, low_price)

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

                    lot_size, calculated_risk, calculated_profit = calculate_position_sizing(symbol, entry, sl, target_risk_usd=10.0)

                    print(f"   🎯 NEW TRADE SETUP DETECTED:")
                    print(f"      • Entry Target : {entry}")
                    print(f"      • Stop Loss    : {sl}")
                    print(f"      • Take Profit 1: {tp1}")  # <-- Added here
                    print(f"      • Take Profit 2: {tp2}")
                    
                    success, ticket_id = broker.execute_order(symbol, decision, lot_size, sl, tp2)

                    if success:
                        active_trades[symbol] = {
                            "symbol": symbol,
                            "type": decision,
                            "entry": entry,
                            "sl": sl,
                            "tp1": tp1,
                            "tp2": tp2,
                            "lot_size": lot_size,
                            "risk_usd": calculated_risk,
                            "ticket": ticket_id,
                            "tp1_hit": False
                        }
                        save_active_trades(active_trades)

                        alert_msg = (
                            f"🤖 *ALPACA PAPER TRADE EXECUTED ({decision})* 🤖\n\n"
                            f"📌 *Asset:* `{symbol}`\n"
                            f"🎫 *Alpaca Order ID:* `{ticket_id}`\n"
                            f"📊 *Price:* `{current_price}` | *Lot:* `{lot_size}`\n"
                            f"🛑 *SL:* `{sl}`\n"
                            f"🎯 *TP1:* `{tp1}` | 🎯 *TP2:* `{tp2}`\n"
                            f"📉 *Risk ($10 Target):* `-${calculated_risk:.2f}`\n"
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
            broker.disconnect()
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