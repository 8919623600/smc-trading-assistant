import pandas as pd
import numpy as np

class SMCTradingEngine:
    def __init__(self, min_rr=2.5, max_rr=6.0, backtest_mode=True):
        self.min_rr = min_rr
        self.max_rr = max_rr
        self.backtest_mode = backtest_mode

    def analyze(self, data_dict):
        try:
            df_1h = data_dict.get("1H")
            df_15m = data_dict.get("15M")
            df_1m_raw = data_dict.get("1M")

            if df_1m_raw is None or len(df_1m_raw) < 50 or df_1h is None or len(df_1h) < 20 or df_15m is None or len(df_15m) < 20:
                return {"decision": "HOLD", "reason": "Insufficient data"}

            df_1m = df_1m_raw.copy()
            current_bar = df_1m.iloc[-1]
            current_close = current_bar["close"]
            current_time = current_bar["datetime"]

            # --- 1. KILLZONE FILTER (London & NY Open Sessions Only) ---
            hour = current_time.hour
            is_london_open = 7 <= hour <= 10
            is_ny_open = 12 <= hour <= 15
            if not (is_london_open or is_ny_open):
                return {"decision": "HOLD", "reason": "Outside Institutional Killzones"}

            # --- 2. HIGHER TIMEFRAME BIAS (1H Structure via EMA crossover) ---
            df_1h["ema_20"] = df_1h["close"].ewm(span=20, adjust=False).mean()
            df_1h["ema_50"] = df_1h["close"].ewm(span=50, adjust=False).mean()
            htf_bullish = df_1h["ema_20"].iloc[-1] > df_1h["ema_50"].iloc[-1]

            # --- 3. 15M ORDER BLOCK POI ---
            df_15m["body"] = df_15m["close"] - df_15m["open"]
            recent_15m = df_15m.iloc[-12:-1]
            
            if htf_bullish:
                down_candles = recent_15m[recent_15m["body"] < 0]
                if len(down_candles) == 0:
                    return {"decision": "HOLD", "reason": "No valid 15M Bullish OB"}
                ob_zone_high = down_candles["high"].iloc[-1]
                ob_zone_low = down_candles["low"].iloc[-1]
            else:
                up_candles = recent_15m[recent_15m["body"] > 0]
                if len(up_candles) == 0:
                    return {"decision": "HOLD", "reason": "No valid 15M Bearish OB"}
                ob_zone_high = up_candles["high"].iloc[-1]
                ob_zone_low = up_candles["low"].iloc[-1]

            # Check if price is interacting with the POI zone
            in_poi = ob_zone_low <= current_close <= ob_zone_high
            if not in_poi:
                # Allow a small tolerance wrapper around the POI
                distance = min(abs(current_close - ob_zone_high), abs(current_close - ob_zone_low))
                if distance / current_close > 0.002:
                    return {"decision": "HOLD", "reason": "Price outside POI zone"}

            # --- 4. 1M LIQUIDITY SWEEP & DISPLACEMENT CONFIRMATION ---
            df_1m["tr"] = np.maximum(
                df_1m["high"] - df_1m["low"],
                np.maximum(
                    abs(df_1m["high"] - df_1m["close"].shift(1)),
                    abs(df_1m["low"] - df_1m["close"].shift(1))
                )
            )
            df_1m["atr"] = df_1m["tr"].rolling(14).mean()
            atr = df_1m["atr"].iloc[-1]
            if pd.isna(atr) or atr == 0:
                atr = 2.0

            decision = "HOLD"
            trade_params = {}

            # Check for a sweep of recent 1M lows/highs followed by sharp displacement (Engulfing or strong body)
            recent_low = df_1m["low"].iloc[-6:-2].min()
            recent_high = df_1m["high"].iloc[-6:-2].max()
            
            last_bar = df_1m.iloc[-1]
            prev_bar = df_1m.iloc[-2]

            if htf_bullish:
                # Sweep condition: Did price wick below a recent low, then push back up aggressively?
                swept_liquidity = current_bar["low"] < recent_low
                displacement = (last_bar["close"] - last_bar["open"]) > (atr * 0.7) and last_bar["close"] > prev_bar["high"]
                
                if swept_liquidity or displacement:
                    decision = "BUY"
                    entry = current_close
                    sl = min(df_1m["low"].iloc[-5:]) - (atr * 0.3)
                    risk = abs(entry - sl)
                    if risk <= 0: return {"decision": "HOLD", "reason": "Invalid risk sizing"}
                    tp = entry + (risk * self.min_rr)
                    trade_params = {"entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2)}

            else:
                swept_liquidity = current_bar["high"] > recent_high
                displacement = (last_bar["open"] - last_bar["close"]) > (atr * 0.7) and last_bar["close"] < prev_bar["low"]
                
                if swept_liquidity or displacement:
                    decision = "SELL"
                    entry = current_close
                    sl = max(df_1m["high"].iloc[-5:]) + (atr * 0.3)
                    risk = abs(entry - sl)
                    if risk <= 0: return {"decision": "HOLD", "reason": "Invalid risk sizing"}
                    tp = entry - (risk * self.min_rr)
                    trade_params = {"entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2)}

            return {"decision": decision, "trade_params": trade_params, "reason": "Institutional Sweep + Displacement Verified"}

        except Exception as e:
            return {"decision": "HOLD", "reason": f"Error in engine: {str(e)}"}