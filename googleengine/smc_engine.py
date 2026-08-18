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
    """Institutional Smart Money Concepts (SMC) State Machine Engine.

    Enforces strict structural hierarchy:
    4H Bias -> 1H Liquidity Sweep -> 15M CHoCH/Displacement ->
    15M BOS -> POI Confluence (OB + FVG) -> 1M Confirmation -> R:R Validation.
    """

    def __init__(
        self,
        min_rr=2.0,
        max_rr=8.0,
        atr_multiplier=0.4,
        news_buffer_mins=15,
    ):
        self.min_rr = min_rr
        self.max_rr = max_rr
        self.atr_multiplier = atr_multiplier
        self.news_buffer_mins = news_buffer_mins

    # ==========================================
    # CORE TECHNICAL INDICATORS & HELPERS
    # ==========================================
    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculates Average True Range (ATR) for dynamic stop-loss buffers."""
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        return true_range.rolling(period).mean()

    @staticmethod
    def find_pivots(df: pd.DataFrame, length: int = 2):
        """Identifies Swing Highs and Swing Lows using rolling windows."""
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
    def check_displacement(df: pd.DataFrame, lookback: int = 15) -> bool:
        """Validates institutional momentum by checking if candle body > 1.3x average body size."""
        if len(df) < lookback:
            return True
        bodies = (df["close"] - df["open"]).abs()
        avg_body = bodies.iloc[-lookback:-1].mean()
        latest_body = bodies.iloc[-1]
        return latest_body >= (1.3 * avg_body)

    # ==========================================
    # STATE 1: 4H MACRO BIAS & DEALING RANGE
    # ==========================================
    def analyze_4h_bias(self, df_4h: pd.DataFrame) -> dict:
        """State 1: Establishes macro dealing range, equilibrium, and OTE premium/discount zones."""
        df = self.find_pivots(df_4h, length=5)
        highs = df["pivot_high"].dropna()
        lows = df["pivot_low"].dropna()

        recent_high = highs.iloc[-1] if not highs.empty else df["high"].max()
        recent_low = lows.iloc[-1] if not lows.empty else df["low"].min()

        total_range = recent_high - recent_low
        equilibrium = (recent_high + recent_low) / 2
        current_close = df["close"].iloc[-1]

        # OTE Zones (0.618 - 0.790 Fib Retracement)
        ote_bullish_high = recent_high - (total_range * 0.618)
        ote_bullish_low = recent_high - (total_range * 0.790)

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

    # ==========================================
    # STATE 2: 1H LIQUIDITY SWEEP DETECTION
    # ==========================================
    def analyze_1h_liquidity(self, df_1h: pd.DataFrame, bias: str) -> dict:
        """State 2: Detects 1H stop hunts (sweeps of swing highs/lows or equal highs/lows)."""
        df = self.find_pivots(df_1h, length=2)
        swing_highs = df["pivot_high"].dropna()
        swing_lows = df["pivot_low"].dropna()

        last_low = swing_lows.iloc[-1] if not swing_lows.empty else df["low"].min()
        last_high = (
            swing_highs.iloc[-1] if not swing_highs.empty else df["high"].max()
        )
        current_bar = df.iloc[-1]

        swept = False
        sweep_type = "NONE"
        sweep_level = None

        if bias == "BULLISH" and last_low:
            # Price takes out liquidity below recent low then closes back above
            if current_bar["low"] < last_low and current_bar["close"] > last_low:
                swept = True
                sweep_type = "BULLISH"
                sweep_level = current_bar["low"]

        elif bias == "BEARISH" and last_high:
            # Price takes out liquidity above recent high then closes back below
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

    # ==========================================
    # STATE 3 & 4: 15M CHoCH, BOS & POI CONFLUENCE
    # ==========================================
    def analyze_15m_structure_and_poi(self, df_15m: pd.DataFrame, sweep_info: dict) -> dict:
        """State 3, 4 & 5: Validates CHoCH, Displacement, BOS, and composite POI (OB + FVG)."""
        if not sweep_info["swept"]:
            return {"valid_poi": False, "reason": "No 1H liquidity sweep confirmed"}

        df = self.find_pivots(df_15m, length=2)
        swing_highs = df["pivot_high"].dropna()
        swing_lows = df["pivot_low"].dropna()

        m15_sh = swing_highs.iloc[-1] if not swing_highs.empty else df["high"].max()
        m15_sl = swing_lows.iloc[-1] if not swing_lows.empty else df["low"].min()

        # Displacement verification on 15M
        has_displacement = self.check_displacement(df_15m, lookback=15)
        if not has_displacement:
            return {"valid_poi": False, "reason": "15M structure lacks institutional displacement"}

        # Scan for FVG (Fair Value Gap) + Order Block Confluence
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

        # Check if price retested the POI
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

    # ==========================================
    # STATE 6 & 7: 1M CONFIRMATION & R:R VALIDATION
    # ==========================================
    def evaluate_1m_execution(
        self, df_1m: pd.DataFrame, sweep_info: dict, poi_info: dict
    ) -> dict:
        """State 6 & 7: 1M micro confirmation, dynamic ATR stop loss, and R:R validation (2.0R to 8.0R)."""
        if not poi_info["valid_poi"]:
            return {"action": "WAIT", "reason": "15M POI not yet confirmed or retested"}

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
                return {"action": "WAIT", "reason": "Invalid structural risk calculation"}

            tp1 = entry_price + (atr_val * 1.5)
            tp2 = h1_sh
            if tp2 <= entry_price:
                tp2 = entry_price + (risk * 3.0)

            reward = tp2 - entry_price
            rr = reward / risk if risk > 0 else 0.0

            if self.min_rr <= rr <= self.max_rr:
                return {
                    "action": "BUY",
                    "entry": round(entry_price, 5),
                    "sl": round(stop_loss, 5),
                    "tp1": round(tp1, 5),
                    "tp2": round(tp2, 5),
                    "rr": round(rr, 2),
                }

        elif sweep_info["type"] == "BEARISH":
            structural_ceiling = max(m15_sh, h1_sh)
            stop_loss = structural_ceiling + (atr_val * self.atr_multiplier)
            risk = stop_loss - entry_price

            if risk <= 0:
                return {"action": "WAIT", "reason": "Invalid structural risk calculation"}

            tp1 = entry_price - (atr_val * 1.5)
            tp2 = h1_sl
            if tp2 >= entry_price:
                tp2 = entry_price - (risk * 3.0)

            reward = entry_price - tp2
            rr = reward / risk if risk > 0 else 0.0

            if self.min_rr <= rr <= self.max_rr:
                return {
                    "action": "SELL",
                    "entry": round(entry_price, 5),
                    "sl": round(stop_loss, 5),
                    "tp1": round(tp1, 5),
                    "tp2": round(tp2, 5),
                    "rr": round(rr, 2),
                }

        return {
            "action": "WAIT",
            "reason": f"Setup valid but R:R ({rr:.2f}) out of bounds ({self.min_rr}-{self.max_rr})",
        }

    # ==========================================
    # STATE 8: MAIN STATE MACHINE ORCHESTRATOR
    # ==========================================
    def analyze(self, data_dict: dict, news_events: list = None) -> dict:
        """Executes the full sequential institutional state machine."""
        df_1m = data_dict["1M"]
        df_15m = data_dict["15M"]
        current_time = (
            df_1m.index[-1]
            if "time" not in df_1m.columns
            else df_1m.iloc[-1]["time"]
        )

        # News Blackout Verification
        if news_events:
            for event_time in news_events:
                if abs((current_time - event_time).total_seconds()) <= (self.news_buffer_mins * 60):
                    return {
                        "decision": "NO_TRADE",
                        "reason": f"News Blackout Active near {event_time}",
                    }

        # Gate 1: 4H Macro Bias & OTE Zone
        market_context = self.analyze_4h_bias(data_dict["4H"])
        bias = market_context["bias"]
        if bias == "NEUTRAL":
            return {"decision": "NO_TRADE", "reason": "4H Market Bias Neutral"}

        if not market_context["in_ote"]:
            return {
                "decision": "WAIT",
                "reason": "Price not yet in 0.618 - 0.79 OTE Zone (Waiting for deep retracement)",
            }

        # Gate 2: 1H Liquidity Sweep
        sweep = self.analyze_1h_liquidity(data_dict["1H"], bias)
        if not sweep["swept"]:
            return {
                "decision": "WAIT",
                "reason": f"No 1H Liquidity Sweep for {bias} bias",
            }

        # Gate 3, 4 & 5: 15M Structure, CHoCH, BOS & POI Confluence
        poi = self.analyze_15m_structure_and_poi(df_15m, sweep)
        if not poi["valid_poi"]:
            return {
                "decision": "WAIT",
                "reason": poi.get("reason", "15M POI confluence not confirmed"),
            }

        # Gate 6 & 7: 1M Execution & R:R Validation
        execution = self.evaluate_1m_execution(df_1m, sweep, poi)

        return {
            "decision": execution["action"],
            "bias_4h": bias,
            "liquidity_sweep": sweep["type"],
            "trade_params": execution
            if execution["action"] in ["BUY", "SELL"]
            else None,
            "timestamp": str(current_time),
        }