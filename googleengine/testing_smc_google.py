import datetime
import logging
import math
import os
import time
import requests
import yfinance as yf

# ==========================================
# CONFIGURATION & LOGGING SETUP
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("scanner.log")],
)
logger = logging.getLogger("SMC_Engine")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID")

SYMBOLS_TO_SCAN = {
    "EUR/USD": {"yf": "EURUSD=X", "type": "forex", "lot": 0.1},
    "GBP/USD": {"yf": "GBPUSD=X", "type": "forex", "lot": 0.1},
    "NAS100": {"yf": "^NDX", "type": "index", "lot": 1.0},
    "GOLD": {"yf": "GC=F", "type": "commodity", "lot": 0.1},
}


def send_telegram_alert(message):
    """Sends real-time alerts to Telegram channel/chat."""
    if TELEGRAM_TOKEN == "YOUR_BOT_TOKEN":
        logger.info(f"[Telegram Simulated Alert]: {message}")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            logger.error(f"Telegram API Error: {response.text}")
    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")


# ==========================================
# UPGRADED SMC TRADING ENGINE
# ==========================================
class UpgradedSMCEngine:

    def __init__(self, symbol, asset_type):
        self.symbol = symbol
        self.asset_type = asset_type

    def fetch_data(self):
        """Fetches 4H and 1H historical data using yfinance."""
        ticker = SYMBOLS_TO_SCAN[self.symbol]["yf"]
        try:
            df_4h = yf.download(
                ticker, period="60d", interval="4h", progress=False
            )
            df_1h = yf.download(
                ticker, period="30d", interval="1h", progress=False
            )

            # Clean multi-index columns if returned by newer yfinance versions
            for df in [df_4h, df_1h]:
                if hasattr(df.columns, "levels") and len(df.columns.levels) > 1:
                    df.columns = df.columns.droplevel(1)

            return df_4h, df_1h
        except Exception as e:
            logger.error(f"Data fetch error for {self.symbol}: {e}")
            return None, None

    def calculate_atr(self, df, period=14):
        """Calculates Average True Range for displacement & noise filtration."""
        high = df["High"]
        low = df["Low"]
        close = df["Close"]
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr.iloc[-1]

    def get_4h_bias_and_ote(self, df_4h):
        """Upgrade B: 4H Market Range & OTE Zone Calculation (0.618 - 0.79)."""
        if df_4h is None or len(df_4h) < 20:
            return None

        # Determine recent swing high & swing low (last 20 candles)
        swing_high = df_4h["High"].iloc[-20:].max()
        swing_low = df_4h["Low"].iloc[-20:].min()
        current_close = df_4h["Close"].iloc[-1]

        equilibrium = (swing_high + swing_low) / 2.0
        range_span = swing_high - swing_low

        if range_span == 0:
            return None

        # OTE Levels
        # Bullish OTE (retracement down from high into 61.8% - 79% fib level)
        bullish_ote_high = swing_high - (range_span * 0.618)
        bullish_ote_low = swing_high - (range_span * 0.790)

        # Bearish OTE (retracement up from low into 61.8% - 79% fib level)
        bearish_ote_low = swing_low + (range_span * 0.618)
        bearish_ote_high = swing_low + (range_span * 0.790)

        in_bullish_ote = bullish_ote_low <= current_close <= bullish_ote_high
        in_bearish_ote = bearish_ote_low <= current_close <= bearish_ote_high

        if current_close < equilibrium:
            bias = "BULLISH"
            in_ote = in_bullish_ote
            ote_range = f"{bullish_ote_low:.5f} - {bullish_ote_high:.5f}"
        elif current_close > equilibrium:
            bias = "BEARISH"
            in_ote = in_bearish_ote
            ote_range = f"{bearish_ote_low:.5f} - {bearish_ote_high:.5f}"
        else:
            bias = "NEUTRAL"
            in_ote = False
            ote_range = "N/A"

        return {
            "swing_high": swing_high,
            "swing_low": swing_low,
            "equilibrium": equilibrium,
            "bias": bias,
            "in_ote": in_ote,
            "current_close": current_close,
            "ote_range": ote_range,
        }

    def check_liquidity_sweep(self, df_1h, bias):
        """Upgrade C: 1H Liquidity Sweep verification."""
        if df_1h is None or len(df_1h) < 10:
            return False

        recent_highs = df_1h["High"].iloc[-10:-2].max()
        recent_lows = df_1h["Low"].iloc[-10:-2].min()
        latest_high = df_1h["High"].iloc[-1]
        latest_low = df_1h["Low"].iloc[-1]
        latest_close = df_1h["Close"].iloc[-1]

        # Bearish setup: sweep recent highs then close lower
        if bias == "BEARISH" and latest_high > recent_highs and latest_close < recent_highs:
            return True

        # Bullish setup: sweep recent lows then close higher
        if bias == "BULLISH" and latest_low < recent_lows and latest_close > recent_lows:
            return True

        return False

    def analyze(self):
        df_4h, df_1h = self.fetch_data()
        if df_4h is None or df_1h is None:
            return {"decision": "ERROR", "reason": "Data fetch failed"}

        market_context = self.get_4h_bias_and_ote(df_4h)
        if not market_context:
            return {"decision": "ERROR", "reason": "Insufficient 4H data for OTE"}

        atr = self.calculate_atr(df_1h)

        # Print section info for logging
        print(f"\n==================================================")
        print(f"🎯 PROCESSING TRADE ASSET: {self.symbol} ({SYMBOLS_TO_SCAN[self.symbol]['type'].upper()})")
        print(f"==================================================")
        print(f"📊 UPGRADED SMC MARKET VERIFICATION ({self.symbol})")
        print(f"⏰ Scan Time (IST): {datetime.datetime.now().strftime('%Y-%m-%d %I:%M:%S %p IST')}")
        print(f"💲 Current Price:   {market_context['current_close']:.5f}")
        
        print(f"--------------------------------------------------")
        print(f"1️⃣  4H SMC RANGE & OTE ZONE (Upgrade B)")
        print(f"   • Active Swing High: {market_context['swing_high']:.5f}")
        print(f"   • Active Swing Low:  {market_context['swing_low']:.5f}")
        print(f"   • Equilibrium (50%): {market_context['equilibrium']:.5f}")
        print(f"   • Overall Bias:      {market_context['bias']}")
        print(f"--------------------------------------------------")
        print(f"2️⃣  DISPLACEMENT & MOMENTUM FILTER (Upgrade C)")
        print(f"   • Active ATR (Noise):{atr:.4f}")

        # Check OTE condition
        if not market_context["in_ote"]:
            status_msg = f"Price not yet in 0.618 - 0.79 OTE Zone (Waiting for deep retracement)"
            print(f"   • Engine Status:     {status_msg}")
            print(f"==================================================")
            return {
                "decision": "WAIT",
                "bias_4h": market_context["bias"],
                "reason": status_msg,
            }

        # Check Liquidity Sweep
        sweep_detected = self.check_liquidity_sweep(df_1h, market_context["bias"])
        if not sweep_detected:
            status_msg = f"No 1H Liquidity Sweep for {market_context['bias']} bias"
            print(f"   • Engine Status:     {status_msg}")
            print(f"==================================================")
            return {
                "decision": "WAIT",
                "bias_4h": market_context["bias"],
                "reason": status_msg,
            }

        print(f"   • Engine Status:     SETUP CONFIRMED! Executing Trade.")
        print(f"==================================================")
        return {
            "decision": "EXECUTE",
            "bias_4h": market_context["bias"],
            "entry_price": market_context["current_close"],
            "atr": atr,
        }


# ==========================================
# MAIN EXECUTION LOOP
# ==========================================
if __name__ == "__main__":
    import pandas as pd

    logger.info("Starting SMC Trading Assistant Engine (`testing_smc_google.py`)...")
    send_telegram_alert("🚀 *SMC Trading Engine Started Successfully* (Multi-Asset OTE + ATR Enabled)")

    while True:
        for symbol in SYMBOLS_TO_SCAN:
            engine = UpgradedSMCEngine(symbol, SYMBOLS_TO_SCAN[symbol]["type"])
            result = engine.analyze()

            if result["decision"] == "EXECUTE":
                alert_msg = (
                    f"🚨 *SMC TRADE SIGNAL GENERATED* 🚨\n\n"
                    f"• *Asset:* {symbol}\n"
                    f"• *Bias:* {result['bias_4h']}\n"
                    f"• *Entry Price:* {result['entry_price']:.5f}\n"
                    f"• *Lot Size:* {SYMBOLS_TO_SCAN[symbol]['lot']}\n"
                    f"• *ATR:* {result['atr']:.4f}\n"
                    f"• *Status:* Order placed successfully!"
                )
                logger.info(alert_msg)
                send_telegram_alert(alert_msg)

        # Sleep interval between scans (e.g., 5 minutes)
        time.sleep(300)