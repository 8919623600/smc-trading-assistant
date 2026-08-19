import time
from datetime import datetime
from config import SYMBOLS, POLL_INTERVAL_SECONDS
from data_fetcher import TwelveDataFetcher
from smc_engine import AdvancedSMCEngine
from notifier import send_telegram_alert

def run_bot():
    print("==================================================")
    print("🤖 STARTING LIVE SMC MULTI-ASSET TRADING BOT")
    print(f"📊 Monitored Assets: {SYMBOLS}")
    print("==================================================")

    fetcher = TwelveDataFetcher()
    engine = AdvancedSMCEngine(min_rr=1.5, max_rr=5.0)

    last_signals = {symbol: "WAIT" for symbol in SYMBOLS}

    startup_msg = (
        "🚀 *SMC Live Bot Started!*\n"
        f"📊 Assets: {', '.join(SYMBOLS)}\n"
        "⏳ Scanning multi-timeframe structure..."
    )
    send_telegram_alert(startup_msg)

    while True:
        try:
            current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            print(f"\n--- Scan Cycle: {current_time} ---")

            for symbol in SYMBOLS:
                data_dict = fetcher.get_market_data(symbol)
                
                # Validate data availability
                if data_dict["1M"] is None or data_dict["1M"].empty:
                    print(f"⚠️ Skipping {symbol}: No 1M data received.")
                    continue

                signal = engine.analyze(data_dict, symbol=symbol)
                decision = signal["decision"]
                price = signal["current_price"]
                reason = signal["reason"]

                print(f"[{symbol}] Decision: {decision} | Price: {price} | Reason: {reason}")

                # Fire Telegram alert only when decision changes from WAIT to BUY/SELL
                if decision in ["BUY", "SELL"] and last_signals[symbol] != decision:
                    params = signal["trade_params"]
                    alert_msg = (
                        f"🚨 *SMC TRADING SIGNAL DETECTED* 🚨\n\n"
                        f"📌 *Asset:* `{symbol}`\n"
                        f"⚡ *Direction:* `{decision}`\n"
                        f"💵 *Entry Price:* `{params['entry']}`\n"
                        f"🛑 *Stop Loss (SL):* `{params['sl']}`\n"
                        f"🎯 *Take Profit 1:* `{params['tp1']}`\n"
                        f"🎯 *Take Profit 2 (TP2):* `{params['tp2']}`\n"
                        f"⚖️ *Risk-to-Reward:* `1 : {params['rr']}`\n"
                        f"📝 *Reason:* {reason}\n"
                        f"🕒 *Time:* `{current_time}`"
                    )
                    send_telegram_alert(alert_msg)
                    last_signals[symbol] = decision

                elif decision == "WAIT":
                    last_signals[symbol] = "WAIT"

                # Brief pause between symbol requests to respect API rate limits
                time.sleep(2)

        except KeyboardInterrupt:
            print("\n🛑 Bot stopped manually.")
            send_telegram_alert("🛑 *SMC Live Bot Stopped Manually.*")
            break
        except Exception as e:
            print(f"❌ Error in main loop execution: {e}")
            time.sleep(15)
            continue

        print(f"⏳ Waiting {POLL_INTERVAL_SECONDS} seconds for next scan...")
        time.sleep(POLL_INTERVAL_SECONDS)

if __name__ == "__main__":
    run_bot()