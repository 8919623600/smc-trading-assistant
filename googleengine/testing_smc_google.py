from datetime import datetime, time
from zoneinfo import ZoneInfo
import os
import time as t_time
import numpy as np
import pandas as pd
import requests

# Global IST Timezone Definition
IST = ZoneInfo("Asia/Kolkata")


def get_current_ist_time():
    """Utility helper to return current formatted IST time string."""
    return datetime.now(IST).strftime("%Y-%m-%d %I:%M:%S %p IST")


def is_within_trading_hours(symbol: str) -> bool:
    """
    Validates if the current IST time falls within the allowed trading sessions:
    - EUR/USD: 1:30 PM to 12:00 AM IST
    - Gold (XAU/USD): 1:30 PM to 5:00 PM AND 7:30 PM to 12:00 AM IST
    """
    now = datetime.now(IST)
    current_time = now.time()
    
    sym = symbol.upper().replace("/", "").replace("_", "")
    
    # EUR/USD: 1:30 PM (13:30) to 12:00 AM (00:00)
    if "EURUSD" in sym:
        start_time = time(13, 30)
        end_time = time(0, 0)
        if current_time >= start_time or current_time < end_time:
            return True
            
    # Gold (XAU/USD): 1:30 PM - 5:00 PM AND 7:30 PM - 12:00 AM
    elif "XAU" in sym or "GOLD" in sym:
        s1_start = time(13, 30)
        s1_end = time(17, 0)
        
        s2_start = time(19, 30)
        s2_end = time(0, 0)
        
        if s1_start <= current_time <= s1_end:
            return True
        if current_time >= s2_start or current_time < s2_end:
            return True
            
    return False


def send_telegram_alert(message: str):
    """Sends notification alerts directly to Telegram."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("Telegram credentials not found in environment variables.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if not response.json().get("ok"):
            print(f"Failed to send Telegram alert: {response.text}")
    except Exception as e:
        print(f"Error sending Telegram alert: {e}")


class SMCTradingEngine:

    def __init__(
        self,
        min_rr=1.5,
        max_rr=8.0,
        atr_multiplier=0.3,
        news_buffer_mins=15,
    ):
        self.min_rr = min_rr
        self.max_rr = max_rr
        self.atr_multiplier = atr_multiplier
        self.news_buffer_mins = news_buffer_mins

    # ==========================================
    # HELPER FUNCTIONS & INDICATORS
    # ==========================================
    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculates Average True Range (ATR) for dynamic stop-loss buffer."""
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        return true_range.rolling(period).mean()

    @staticmethod
    def find_pivots(df: pd.DataFrame, length: int = 2):
        """Identifies Swing Highs and Swing Lows."""
        df = df.copy()
        df["pivot_high"] = np.nan
        df["pivot_low"] = np.nan

        for i in range(length, len(df) - length):
            window = df.iloc[i - length : i + length + 1]
            if df["high"].iloc[i] == window["high"].max():
                df.iloc[i, df.columns.get_loc("pivot_high")] = df["high"].iloc[i]
            if df["low"].iloc[i] == window["low"].min():
                df.iloc[i, df.columns.get_loc("pivot_low")] = df["low"].iloc[i]

        return df

    # ==========================================
    # TIMEFRAME ANALYSIS STEPS
    # ==========================================
    def get_4h_bias(self, df_4h: pd.DataFrame) -> str:
        """Step 1: 4H Market Bias & Dealing Range (Premium/Discount)."""
        df = self.find_pivots(df_4h, length=5)
        recent_high = (
            df["pivot_high"].dropna().iloc[-1]
            if not df["pivot_high"].dropna().empty
            else df["high"].max()
        )
        recent_low = (
            df["pivot_low"].dropna().iloc[-1]
            if not df["pivot_low"].dropna().empty
            else df["low"].min()
        )

        equilibrium = (recent_high + recent_low) / 2
        current_close = df["close"].iloc[-1]

        if current_close > equilibrium:
            return "BEARISH"  # In Premium: Look for Shorts
        elif current_close < equilibrium:
            return "BULLISH"  # In Discount: Look for Longs
        return "NEUTRAL"

    def check_1h_liquidity_sweep(self, df_1h: pd.DataFrame, bias: str) -> dict:
        """Step 2: Detect 1H Liquidity Sweeps and extract liquidity pools."""
        df = self.find_pivots(df_1h, length=2)
        swing_highs = df["pivot_high"].dropna()
        swing_lows = df["pivot_low"].dropna()

        last_low = swing_lows.iloc[-1] if not swing_lows.empty else df["low"].min()
        last_high = swing_highs.iloc[-1] if not swing_highs.empty else df["high"].max()

        current_bar = df.iloc[-1]

        swept = False
        sweep_type = "NONE"
        sweep_level = None

        if bias == "BULLISH" and last_low:
            if current_bar["low"] < last_low and current_bar["close"] > last_low:
                swept = True
                sweep_type = "BULLISH"
                sweep_level = current_bar["low"]

        elif bias == "BEARISH" and last_high:
            if current_bar["high"] > last_high and current_bar["close"] < last_high:
                swept = True
                sweep_type = "BEARISH"
                sweep_level = current_bar["high"]

        return {
            "swept": swept,
            "type": sweep_type,
            "sweep_level": sweep_level,
            "h1_sh": last_high,
            "h1_sl": last_low
        }

    def detect_15m_poi(self, df_15m: pd.DataFrame, sweep_info: dict) -> dict:
        """Step 3: 15M Structure Shift & POI (OB + FVG)."""
        if not sweep_info["swept"]:
            return {"valid_poi": False}

        df = self.find_pivots(df_15m, length=2)
        swing_highs = df["pivot_high"].dropna()
        swing_lows = df["pivot_low"].dropna()

        m15_sh = swing_highs.iloc[-1] if not swing_highs.empty else df["high"].max()
        m15_sl = swing_lows.iloc[-1] if not swing_lows.empty else df["low"].min()

        fvg_found = False
        fvg_top, fvg_bottom = None, None

        start_idx = len(df) - 3
        end_idx = max(2, len(df) - 10)

        for i in range(start_idx, end_idx, -1):
            if sweep_info["type"] == "BULLISH":
                if df["low"].iloc[i] > df["high"].iloc[i - 2]:  # Bullish FVG
                    fvg_found = True
                    fvg_top = df["low"].iloc[i]
                    fvg_bottom = df["high"].iloc[i - 2]
                    break
            elif sweep_info["type"] == "BEARISH":
                if df["high"].iloc[i] < df["low"].iloc[i - 2]:  # Bearish FVG
                    fvg_found = True
                    fvg_top = df["low"].iloc[i - 2]
                    fvg_bottom = df["high"].iloc[i]
                    break

        retested = False
        if fvg_found:
            if sweep_info["type"] == "BULLISH" and df["low"].iloc[-1] <= fvg_top:
                retested = True
            elif sweep_info["type"] == "BEARISH" and df["high"].iloc[-1] >= fvg_bottom:
                retested = True

        return {
            "valid_poi": fvg_found and retested,
            "fvg_top": fvg_top,
            "fvg_bottom": fvg_bottom,
            "m15_sh": m15_sh,
            "m15_sl": m15_sl
        }

    def evaluate_1m_entry(
        self, df_1m: pd.DataFrame, sweep_info: dict, poi_info: dict
    ) -> dict:
        """Step 4: 1M Entry, Tight SL with ATR buffer, TP1 (1.5R), and TP2 (1H Liquidity Pool)."""
        if not poi_info["valid_poi"]:
            return {"action": "NO_TRADE", "reason": "No valid 15M POI retest"}

        df = df_1m.copy()
        df["atr"] = self.calculate_atr(df, 14)
        current_bar = df.iloc[-1]
        atr_val = current_bar["atr"] if not pd.isna(current_bar["atr"]) else 0.0001

        entry_price = current_bar["close"]
        h1_sh = sweep_info["h1_sh"]
        h1_sl = sweep_info["h1_sl"]
        m15_sh = poi_info["m15_sh"]
        m15_sl = poi_info["m15_sl"]

        if sweep_info["type"] == "BULLISH":
            structural_floor = min(m15_sl, h1_sl)
            stop_loss = structural_floor - (atr_val * self.atr_multiplier)
            risk = entry_price - stop_loss
            
            if risk <= 0:
                return {"action": "WAIT", "reason": "Calculated risk is invalid or zero"}

            tp1 = entry_price + (risk * 1.5)  # Breakeven target
            tp2 = h1_sh                       # 1H Structural Liquidity Target
            if tp2 <= entry_price:
                tp2 = entry_price + (risk * 2.0)

            reward_tp2 = tp2 - entry_price
            rr_tp2 = reward_tp2 / risk

            if self.min_rr <= rr_tp2 <= self.max_rr:
                return {
                    "action": "BUY",
                    "entry": round(entry_price, 5),
                    "sl": round(stop_loss, 5),
                    "tp1": round(tp1, 5),
                    "tp2": round(tp2, 5),
                    "rr": round(rr_tp2, 2),
                }

        elif sweep_info["type"] == "BEARISH":
            structural_ceiling = max(m15_sh, h1_sh)
            stop_loss = structural_ceiling + (atr_val * self.atr_multiplier)
            risk = stop_loss - entry_price
            
            if risk <= 0:
                return {"action": "WAIT", "reason": "Calculated risk is invalid or zero"}

            tp1 = entry_price - (risk * 1.5)  # Breakeven target
            tp2 = h1_sl                       # 1H Structural Liquidity Target
            if tp2 >= entry_price:
                tp2 = entry_price - (risk * 2.0)

            reward_tp2 = entry_price - tp2
            rr_tp2 = reward_tp2 / risk

            if self.min_rr <= rr_tp2 <= self.max_rr:
                return {
                    "action": "SELL",
                    "entry": round(entry_price, 5),
                    "sl": round(stop_loss, 5),
                    "tp1": round(tp1, 5),
                    "tp2": round(tp2, 5),
                    "rr": round(rr_tp2, 2),
                }

        return {
            "action": "WAIT",
            "reason": "Setup conditions met but 1H Liquidity R:R out of bounds",
        }

    # ==========================================
    # MAIN ANALYZER RUNNER
    # ==========================================
    def analyze(self, symbol: str, data_dict: dict, news_events: list = None) -> dict:
        """Executes session time validation and full SMC top-down cascade."""
        
        # Enforce Session Time Check
        if not is_within_trading_hours(symbol):
            return {
                "decision": "OUT_OF_SESSION",
                "reason": f"Current IST time is outside active trading session for {symbol}"
            }

        df_1m = data_dict["1M"]
        current_time = (
            df_1m.index[-1]
            if "time" not in df_1m.columns
            else df_1m.iloc[-1]["time"]
        )

        # News Blackout Check
        if news_events:
            for event_time in news_events:
                if (
                    abs((current_time - event_time).total_seconds())
                    <= (self.news_buffer_mins * 60)
                ):
                    return {
                        "decision": "NO_TRADE",
                        "reason": f"News Blackout Active near {event_time}",
                    }

        # Step 1: 4H Market Bias
        bias = self.get_4h_bias(data_dict["4H"])
        if bias == "NEUTRAL":
            return {"decision": "NO_TRADE", "reason": "4H Market Bias Neutral"}

        # Step 2: 1H Liquidity Sweep & Levels
        sweep = self.check_1h_liquidity_sweep(data_dict["1H"], bias)
        if not sweep["swept"]:
            return {
                "decision": "WAIT",
                "reason": f"No 1H Liquidity Sweep for {bias} bias",
            }

        # Step 3: 15M POI & Retest
        poi = self.detect_15m_poi(data_dict["15M"], sweep)
        if not poi["valid_poi"]:
            return {
                "decision": "WAIT",
                "reason": "15M POI not confirmed or retested",
            }

        # Step 4: 1M Precision Entry with 1H Liquidity Targets
        entry = self.evaluate_1m_entry(df_1m, sweep, poi)

        result = {
            "symbol": symbol,
            "decision": entry["action"],
            "bias_4h": bias,
            "liquidity_sweep": sweep["type"],
            "trade_params": entry if entry["action"] in ["BUY", "SELL"] else None,
            "timestamp": str(current_time),
        }

        # Send Telegram alert if a valid signal is generated
        if result["decision"] in ["BUY", "SELL"]:
            tp = result["trade_params"]
            msg = (
                f"🚨 *SMC TRADE SIGNAL: {symbol}* 🚨\n\n"
                f"🔹 *Action:* `{result['decision']}`\n"
                f"📈 *4H Bias:* {result['bias_4h']}\n"
                f"🎯 *Entry:* `{tp['entry']}`\n"
                f"🛑 *Stop Loss:* `{tp['sl']}`\n"
                f"🎯 *TP1 (1.5R):* `{tp['tp1']}`\n"
                f"🎯 *TP2 (1H Pool):* `{tp['tp2']}`\n"
                f"⚖️ *R:R (TP2):* `{tp['rr']}R`\n"
                f"🕒 *Time:* {get_current_ist_time()}"
            )
            send_telegram_alert(msg)

        return result