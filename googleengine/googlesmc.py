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
        min_rr=1.5,
        max_rr=8.0,
        atr_multiplier=0.5,  # Updated from 0.3 to 0.5 for a tight structural swing buffer
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

    @staticmethod
    def check_displacement(df_15m: pd.DataFrame) -> bool:
        """UPGRADE C: Validates if the recent impulse features true institutional displacement.
        Blocks trades if candles feature tiny bodies and massive rejection wicks.
        """
        if len(df_15m) < 10:
            return True

        bodies = (df_15m["close"] - df_15m["open"]).abs()
        avg_body = bodies.iloc[-15:-1].mean()
        latest_body = bodies.iloc[-1]

        # Ensure latest candle body is at least 1.3x the average body size
        return latest_body >= (1.3 * avg_body)

    # ==========================================
    # TIMEFRAME ANALYSIS STEPS
    # ==========================================
    def get_4h_bias_and_ote(self, df_4h: pd.DataFrame) -> dict:
        """Step 1: 4H Market Bias & Upgraded OTE Zone (0.618 - 0.79 Fib Retracement)."""
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

        total_range = recent_high - recent_low
        equilibrium = (recent_high + recent_low) / 2
        current_close = df["close"].iloc[-1]

        # UPGRADE B: Optimal Trade Entry (OTE) Zone Calculations
        # Bullish OTE: Retracement down into 61.8% to 79% of the discount array
        ote_bullish_high = recent_high - (total_range * 0.618)
        ote_bullish_low = recent_high - (total_range * 0.790)

        # Bearish OTE: Retracement up into 61.8% to 79% of the premium array
        ote_bearish_low = recent_low + (total_range * 0.618)
        ote_bearish_high = recent_low + (total_range * 0.790)

        in_bullish_ote = ote_bullish_low <= current_close <= ote_bullish_high
        in_bearish_ote = ote_bearish_low <= current_close <= ote_bearish_high

        if current_close < equilibrium:
            bias = "BULLISH"
            in_ote = in_bullish_ote
        elif current_close > equilibrium:
            bias = "BEARISH"
            in_ote = in_bearish_ote
        else:
            bias = "NEUTRAL"
            in_ote = False

        return {
            "bias": bias,
            "in_ote": in_ote,
            "recent_high": recent_high,
            "recent_low": recent_low,
            "equilibrium": equilibrium,
        }

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
            "h1_sl": last_low,
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
            "m15_sl": m15_sl,
        }

    def evaluate_1m_entry(
        self, df_1m: pd.DataFrame, sweep_info: dict, poi_info: dict
    ) -> dict:
        """Step 4: 1M Entry, Tight SL with ATR buffer, TP1 (1.2x ATR / internal structural target), and TP2 (1H Liquidity Pool)."""
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

            # TP1: 15M internal structural target for partials (approx 1.2x ATR or structural offset)
            tp1 = entry_price + (atr_val * 1.2)
            # TP2: 1H external liquidity pool / opposing structural extreme
            tp2 = h1_sh
            if tp2 <= entry_price:
                tp2 = entry_price + (risk * 3.0)

            reward_tp2 = tp2 - entry_price
            rr_tp2 = reward_tp2 / risk if risk > 0 else 0.0

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

            # TP1: 15M internal structural target for partials
            tp1 = entry_price - (atr_val * 1.2)
            # TP2: 1H external liquidity pool / opposing structural extreme
            tp2 = h1_sl
            if tp2 >= entry_price:
                tp2 = entry_price - (risk * 3.0)

            reward_tp2 = entry_price - tp2
            rr_tp2 = reward_tp2 / risk if risk > 0 else 0.0

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
    def analyze(self, data_dict: dict, news_events: list = None) -> dict:
        """Executes the full SMC top-down cascade with OTE and Displacement filters."""
        df_1m = data_dict["1M"]
        df_15m = data_dict["15M"]
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

        # Step 1: 4H Market Bias & OTE Zone Check (Upgrade B)
        market_context = self.get_4h_bias_and_ote(data_dict["4H"])
        bias = market_context["bias"]
        if bias == "NEUTRAL":
            return {"decision": "NO_TRADE", "reason": "4H Market Bias Neutral"}

        # Optional strict OTE gate check: if not in OTE sweet spot, wait for deeper pullback
        if not market_context["in_ote"]:
            return {
                "decision": "WAIT",
                "reason": "Price not yet in 0.618 - 0.79 OTE Zone (Waiting for deep retracement)",
            }

        # Step 2: 1H Liquidity Sweep & Levels
        sweep = self.check_1h_liquidity_sweep(data_dict["1H"], bias)
        if not sweep["swept"]:
            return {
                "decision": "WAIT",
                "reason": f"No 1H Liquidity Sweep for {bias} bias",
            }

        # Step 3: 15M POI & Retest
        poi = self.detect_15m_poi(df_15m, sweep)
        if not poi["valid_poi"]:
            return {
                "decision": "WAIT",
                "reason": "15M POI not confirmed or retested",
            }

        # Step 3.5: True Displacement Filter Check (Upgrade C)
        has_displacement = self.check_displacement(df_15m)
        if not has_displacement:
            return {
                "decision": "WAIT",
                "reason": "Trade Blocked: Lacks institutional displacement momentum (Weak body/Wick rejection)",
            }

        # Step 4: 1M Precision Entry with 1H Liquidity Targets
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