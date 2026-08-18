import pandas as pd
import numpy as np

class SMCTradingEngine:
    def __init__(self, min_rr=2.0, max_rr=6.0, backtest_mode=True):
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

            # --- 2. HIGHER TIMEFRAME BIAS (1H Structure) ---
            df_1h["sma_50"] = df_1h["close"].rolling(50).mean()
            htf_bullish = df_1h["close"].iloc[-1] > df_1h["sma_50"].iloc[-1]

            # --- 3. 15M ORDER BLOCK (POI) DETECTION ---
            # Find a bullish/bearish impulse candle cluster on 15M
            df_15m["body"] = df_15m["close"] - df_15m["open"]
            df_15m["range"] = df_15m["high"] - df_15m["low"]
            
            recent_15m = df_15m.iloc[-10:-1] # Look at recent completed 15M bars
            if htf_bullish:
                # Look for the last down-candle before a strong expansion up
                down_candles = recent_15m[recent_15m["body"] < 0]
                if len(down_candles) == 0:
                    return {"decision": "HOLD", "reason": "No valid 15M Bullish OB found"}
                ob_zone_high = down_candles["high"].iloc[-1]
                ob_zone_low = down_candles["low"].iloc[-1]
                
                # Check if price has tapped into the 15M Order Block zone
                in_poi = ob_zone_low <= current_close <= ob_zone_high
                if not in_poi and current_close > ob_zone_high:
                    # Check if price is within a reasonable pullback distance (0.5% max)
                    if (current_close - ob_zone_high) / ob_zone_high > 0.003:
                        return {"decision": "HOLD", "reason": "Price too far from 15M Bullish OB"}

            else:
                # Bearish OB
                up_candles = recent_15m[recent_15m["body"] > 0]
                if len(up_candles) == 0:
                    return {"decision": "HOLD", "reason": "No valid 15M Bearish OB found"}
                ob_zone_high = up_candles["high"].iloc[-1]
                ob_zone_low = up_candles["low"].iloc[-1]
                
                in_poi = ob_zone_low <= current_close <= ob_zone_high
                if not in_poi and current_close < ob_zone_low:
                    if (ob_zone_low - current_close) / ob_zone_low > 0.003:
                        return {"decision": "HOLD", "reason": "Price too far from 15M Bearish OB"}

            # --- 4. 1M ATR & CHOCH (Change of Character) CONFIRMATION ---
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

            # 1M confirmation: 3 consecutive higher closes for bullish, lower for bearish inside the zone
            if htf_bullish:
                recent_1m_closes = df_1m["close"].iloc[-3:].values
                is_choch_bullish = (recent_1m_closes[2] > recent_1m_closes[1]) and (recent_1m_closes[1] > recent_1m_closes[0])
                
                if is_choch_bullish:
                    decision = "BUY"
                    entry = current_close
                    sl = min(df_1m["low"].iloc[-5:]) - (atr * 0.5) # Tight structural SL below 1M swing low
                    risk = abs(entry - sl)
                    tp = entry + (risk * 2.5) # 2.5 RR Target
                    trade_params = {"entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2)}

            else:
                recent_1m_closes = df_1m["close"].iloc[-3:].values
                is_choch_bearish = (recent_1m_closes[2] < recent_1m_closes[1]) and (recent_1m_closes[1] < recent_1m_closes[0])
                
                if is_choch_bearish:
                    decision = "SELL"
                    entry = current_close
                    sl = max(df_1m["high"].iloc[-5:]) + (atr * 0.5) # Tight structural SL above 1M swing high
                    risk = abs(entry - sl)
                    tp = entry - (risk * 2.5)
                    trade_params = {"entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2)}

            return {"decision": decision, "trade_params": trade_params, "reason": "Institutional OB + Killzone Choch Confirmed"}

        except Exception as e:
            return {"decision": "HOLD", "reason": f"Error in engine: {str(e)}"}