from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd

# Global IST Timezone Definition
IST = ZoneInfo("Asia/Kolkata")


def get_current_ist_time():
    """Utility helper to return current formatted IST time string."""
    return datetime.now(IST).strftime("%Y-%m-%d %I:%M:%S %p IST")


class SMCTradingEngine:

    def __init__(
        self,
        min_rr=2.0,
        max_rr=8.0,
        atr_multiplier=1.0,
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
    def find_pivots(df: pd.DataFrame, length: int = 5):
        """Identifies Swing Highs and Swing Lows."""
        df = df.copy()
        df["pivot_high"] = np.nan
        df["pivot_low"] = np.nan

        for i in range(length, len(df) - length):
            window = df.iloc[i - length : i + length + 1]
            if df["high"].iloc[i] == window["high"].max():
                df.iloc[i, df.columns.get_loc("pivot_high")] = df["high"].iloc[
                    i
                ]
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
        """Step 2: Detect 1H Liquidity Sweeps."""
        df = self.find_pivots(df_1h, length=5)
        last_low = (
            df["pivot_low"].dropna().iloc[-1]
            if not df["pivot_low"].dropna().empty
            else None
        )
        last_high = (
            df["pivot_high"].dropna().iloc[-1]
            if not df["pivot_high"].dropna().empty
            else None
        )

        current_bar = df.iloc[-1]

        if bias == "BULLISH" and last_low:
            if (
                current_bar["low"] < last_low
                and current_bar["close"] > last_low
            ):
                return {
                    "swept": True,
                    "type": "BULLISH",
                    "sweep_level": current_bar["low"],
                }

        elif bias == "BEARISH" and last_high:
            if (
                current_bar["high"] > last_high
                and current_bar["close"] < last_high
            ):
                return {
                    "swept": True,
                    "type": "BEARISH",
                    "sweep_level": current_bar["high"],
                }

        return {"swept": False, "type": "NONE", "sweep_level": None}

    def detect_15m_poi(self, df_15m: pd.DataFrame, sweep_info: dict) -> dict:
        """Step 3: 15M Structure Shift (CHoCH + BOS) & POI (OB + FVG)."""
        if not sweep_info["swept"]:
            return {"valid_poi": False}

        df = self.find_pivots(df_15m, length=3)

        fvg_found = False
        fvg_top, fvg_bottom = None, None

        # Fixed index bound check to prevent negative wrapping
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

        # Check if current price returned to POI
        retested = False
        if fvg_found:
            if (
                sweep_info["type"] == "BULLISH"
                and df["low"].iloc[-1] <= fvg_top
            ):
                retested = True
            elif (
                sweep_info["type"] == "BEARISH"
                and df["high"].iloc[-1] >= fvg_bottom
            ):
                retested = True

        return {
            "valid_poi": fvg_found and retested,
            "fvg_top": fvg_top,
            "fvg_bottom": fvg_bottom,
        }

    def evaluate_1m_entry(
        self, df_1m: pd.DataFrame, sweep_info: dict, poi_info: dict
    ) -> dict:
        """Step 4: 1M Micro CHoCH & Risk Engine Validation."""
        if not poi_info["valid_poi"]:
            return {"action": "NO_TRADE", "reason": "No valid 15M POI retest"}

        df = df_1m.copy()
        df["atr"] = self.calculate_atr(df, 14)
        current_bar = df.iloc[-1]
        atr_val = current_bar["atr"]

        entry_price = current_bar["close"]

        if sweep_info["type"] == "BULLISH":
            stop_loss = sweep_info["sweep_level"] - (
                atr_val * self.atr_multiplier
            )
            risk = entry_price - stop_loss
            target_tp = entry_price + (risk * self.min_rr)
            rr = (target_tp - entry_price) / risk if risk > 0 else 0

            if self.min_rr <= rr <= self.max_rr:
                return {
                    "action": "BUY",
                    "entry": round(entry_price, 3),
                    "sl": round(stop_loss, 3),
                    "tp": round(target_tp, 3),
                    "rr": round(rr, 2),
                }

        elif sweep_info["type"] == "BEARISH":
            stop_loss = sweep_info["sweep_level"] + (
                atr_val * self.atr_multiplier
            )
            risk = stop_loss - entry_price
            target_tp = entry_price - (risk * self.min_rr)
            rr = (entry_price - target_tp) / risk if risk > 0 else 0

            if self.min_rr <= rr <= self.max_rr:
                return {
                    "action": "SELL",
                    "entry": round(entry_price, 3),
                    "sl": round(stop_loss, 3),
                    "tp": round(target_tp, 3),
                    "rr": round(rr, 2),
                }

        return {
            "action": "WAIT",
            "reason": "Setup conditions met but Risk-to-Reward invalid",
        }

    # ==========================================
    # MAIN ANALYZER RUNNER
    # ==========================================
    def analyze(self, data_dict: dict, news_events: list = None) -> dict:
        """Executes the full SMC top-down cascade."""
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

        # Step 2: 1H Liquidity Sweep
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

        # Step 4: 1M Precision Entry
        entry = self.evaluate_1m_entry(df_1m, sweep, poi)

        return {
            "decision": entry["action"],
            "bias_4h": bias,
            "liquidity_sweep": sweep["type"],
            "trade_params": entry
            if entry["action"] in ["BUY", "SELL"]
            else None,
            "timestamp": str(current_time),
        }