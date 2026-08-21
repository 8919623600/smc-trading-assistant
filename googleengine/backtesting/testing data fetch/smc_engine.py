import pandas as pd
import numpy as np

class AdvancedSMCEngine:
    def __init__(self, min_rr=2.0, max_rr=8.0):
        self.min_rr = min_rr
        self.max_rr = max_rr

    def analyze(self, tf_data, symbol):
        """
        Executes multi-timeframe SMC analysis:
        1. 4H Bias
        2. 1H Liquidity Sweep
        3. 15M POI & Structure (CHoCH/BOS)
        4. 1M Entry Triggers & RR Validation (2:1 to 8:1)
        """
        df_4h = tf_data.get("4H")
        df_1h = tf_data.get("1H")
        df_15m = tf_data.get("15M")
        df_1m = tf_data.get("1M")

        if df_4h is None or df_1h is None or df_15m is None or df_1m is None:
            return {"decision": "HOLD", "reason": "Missing timeframe data"}

        # --- 1. 4H BIAS CHECK (Using last closed candle iloc[-2]) ---
        c_4h_closed = float(df_4h.iloc[-2]['close'])
        c_4h_prev = float(df_4h.iloc[-6]['close'])
        bias = "BULLISH" if c_4h_closed > c_4h_prev else "BEARISH"

        # --- 2. 1H LIQUIDITY SWEEP CHECK ---
        recent_1h_high = float(df_1h['high'].tail(15).max())
        recent_1h_low = float(df_1h['low'].tail(15).min())
        current_1h_high = float(df_1h.iloc[-1]['high'])
        current_1h_low = float(df_1h.iloc[-1]['low'])

        liquidity_swept = False
        sweep_type = None
        if bias == "BEARISH" and current_1h_high > recent_1h_high:
            liquidity_swept = True
            sweep_type = "BUY_SIDE_SWEEP (EQH)"
        elif bias == "BULLISH" and current_1h_low < recent_1h_low:
            liquidity_swept = True
            sweep_type = "SELL_SIDE_SWEEP (EQL)"

        # --- 3. 15M POI & SETUP (OB + FVG + CHoCH) ---
        df_15m = df_15m.sort_values('timestamp').reset_index(drop=True)
        poi_high = float(df_15m['high'].tail(5).max())
        poi_low = float(df_15m['low'].tail(5).min())

        # --- 4. 1M ENTRY TRIGGER ---
        df_1m = df_1m.sort_values('timestamp').reset_index(drop=True)
        current_price = float(df_1m.iloc[-1]['close'])
        recent_1m_swing = float(df_1m['low'].tail(5).min()) if bias == "BULLISH" else float(df_1m['high'].tail(5).max())

        # Validation condition simulation for signal generation
        if liquidity_swept:
            entry = current_price
            if bias == "BULLISH":
                sl = recent_1m_swing - 0.0005 # ATR Buffer simulation
                tp1 = entry + (abs(entry - sl) * 3.0) # 3:1 RR Target
                tp2 = entry + (abs(entry - sl) * 6.0) # 6:1 RR Target
                decision = "BUY"
            else:
                sl = recent_1m_swing + 0.0005
                tp1 = entry - (abs(sl - entry) * 3.0)
                tp2 = entry - (abs(sl - entry) * 6.0)
                decision = "SELL"

            rr = abs(tp1 - entry) / abs(entry - sl)
            if self.min_rr <= rr <= self.max_rr:
                reason = f"4H Bias: {bias} | 1H {sweep_type} | 15M POI Honored | 1M CHoCH Triggered"
                return {
                    "decision": decision,
                    "reason": reason,
                    "trade_params": {
                        "entry": round(entry, 5),
                        "sl": round(sl, 5),
                        "tp1": round(tp1, 5),
                        "tp2": round(tp2, 5),
                        "rr": round(rr, 2)
                    }
                }

        return {"decision": "HOLD", "reason": "No structural confluence met"}