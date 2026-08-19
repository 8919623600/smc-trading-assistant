import time
import os
import csv
import json
from datetime import datetime, timedelta
from config import SYMBOLS, POLL_INTERVAL_SECONDS
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
    """Calculates daily win/loss and net profit from trade_history.csv for a specific date."""
    if not os.path.exists(HISTORY_FILE):
        return

    wins = 0
    losses = 0
    total_pnl = 0.0
    total_trades = 0

    try:
        with open(HISTORY_FILE, mode='r') as f:
            reader = csv.reader(f)
            header = next(reader, None)  # Skip header
            for row in reader:
                if not row or len(row) < 11:
                    continue
                timestamp = row[0]
                trade_date = timestamp.split(' ')[0]  # Extracts YYYY-MM-DD
                
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
        return  # Skip summary if no trades occurred on that day

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
    print(f"📊 Daily Summary sent for {target_date_str} | Net PnL: ${total_pnl:.2f}")

def calculate_position_sizing(symbol, entry, sl, target_risk_usd=10.0):
    risk_points = abs(entry - sl)
    if risk_points <= 0:
        return 0.01, 10.0, 20.0

    is_gold = "XAU" in symbol.upper()
    dollar_risk_per_lot = (risk_points * 100) if is_gold else (risk_points * 10000 * 10)

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
        print(f"[{symbol}] Trade Closed -> {outcome} | PnL: ${pnl:.2f}")

        del active_trades[symbol]
        save_active_trades(active_trades)

def run_bot():
    init_files()
    
    broker = MT5BrokerConnector()
    broker.connect()

    print("==================================================")
    print("🤖 STARTING ISOLATED AUTOMATED SMC PAPER BOT")
    print(f"📊 Monitored Assets: {SYMBOLS}")
    print("==================================================")
    print(f"🔌 Telegram API Connection: ACTIVE ✅")
    print("==================================================")

    fetcher = TwelveDataFetcher()
    engine = AdvancedSMCEngine(min_rr=1.5, max_rr=5.0)

    send_telegram_alert("🚀 *Isolated SMC Paper Bot Online & Ready!*")

    # Track current day to trigger daily summaries
    current_utc_date = datetime.utcnow().strftime('%Y-%m-%d')

    while True:
        try:
            now_utc = datetime.utcnow()
            today_str = now_utc.strftime('%Y-%m-%d')

            # Check if the date has rolled over to a new day
            if today_str != current_utc_date:
                # Send summary for the day that just ended
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

                # Check active trades
                check_active_trades(symbol, current_price, high_price, low_price)

                # Run SMC Engine scan
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
                    rr = params["rr"]

                    lot_size, calculated_risk, calculated_profit = calculate_position_sizing(symbol, entry, sl, target_risk_usd=10.0)

                    print(f"   🎯 NEW TRADE SETUP DETECTED:")
                    print(f"      • Entry Target : {entry}")
                    print(f"      • Stop Loss    : {sl}")
                    print(f"      • Take Profit 2: {tp2}")
                    print(f"   🤖 EXECUTING VIA ISOLATED MT5 CONNECTOR...")
                    
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
                            f"🤖 *AUTOMATED PAPER TRADE EXECUTED ({decision})* 🤖\n\n"
                            f"📌 *Asset:* `{symbol}`\n"
                            f"🎫 *MT5 Ticket ID:* `{ticket_id}`\n"
                            f"📊 *Price:* `{current_price}` | *Lot:* `{lot_size}`\n"
                            f"🛑 *SL:* `{sl}` | 🎯 *TP2:* `{tp2}`\n"
                            f"📉 *Risk ($10 Target):* `-${calculated_risk:.2f}`\n"
                            f"📝 *Reason:* {reason}"
                        )
                        send_telegram_alert(alert_msg)
                    else:
                        print(f"⚠️ Broker execution bypassed or failed. Bot continues running normally.")

                elif symbol in active_trades:
                    print(f"   ⏳ Status: Trade active. Managing SL/TP targets...")
                else:
                    print(f"   ⏳ Status: Market consolidating. Awaiting structure.")

                print("-" * 50)

        except KeyboardInterrupt:
            print("\n🛑 Bot stopped manually by user.")
            broker.disconnect()
            send_telegram_alert("🛑 *Isolated SMC Bot Stopped Manually.*")
            break
        except Exception as e:
            print(f"❌ Error in main execution loop: {e}")
            time.sleep(15)
            continue

        print(f"⏳ Waiting {POLL_INTERVAL_SECONDS} seconds for next candle scan...\n")
        time.sleep(POLL_INTERVAL_SECONDS)

if __name__ == "__main__":
    run_bot()