import pandas as pd
import numpy as np

class SMCTradingEngine:
    def __init__(self, min_rr=2.0, max_rr=8.0, atr_multiplier=0.5, backtest_mode=True):
        self.min_rr = min_rr
        self.max_rr = max_rr
        self.atr_multiplier = atr_multiplier
        self.backtest_mode = backtest_mode

    def analyze(self, data_dict):
        try:
            df_4h = data_dict.get("4H")
            df_1h = data_dict.get("1H")
            df_15m = data_dict.get("15M")
            df_1m_raw = data_dict.get("1M")

            if df_1m_raw is None or len(df_1m_raw) < 50:
                return {"decision": "HOLD", "reason": "Insufficient 1M data"}

            df_1m = df_1m_raw.copy()

            current_bar = df_1m.iloc[-1]
            current_close = current_bar["close"]
            current_high = current_bar["high"]
            current_low = current_bar["low"]

            # --- 1. CALCULATE ATR ---
            df_1m["tr"] = np.maximum(
                df_1m["high"] - df_1m["low"],
                np.maximum(
                    abs(df_1m["high"] - df_1m["close"].shift(1)),
                    abs(df_1m["low"] - df_1m["close"].shift(1))
                )
            )
            atr = df_1m["tr"].rolling(14).mean().iloc[-1]
            if pd.isna(atr) or atr == 0:
                atr = 2.0

            # --- 2. SMC STRUCTURE WITH LOOKBACK WINDOW ---
            recent_high = df_1m["high"].iloc[-25:-3].max()
            recent_low = df_1m["low"].iloc[-25:-3].min()

            # Check if a liquidity sweep happened in the recent past (last 3 bars)
            recent_low_sweep = df_1m["low"].iloc[-3:].min() <= recent_low
            recent_high_sweep = df_1m["high"].iloc[-3:].max() >= recent_high

            # Fair Value Gap (FVG) Detection
            bullish_fvg = df_1m["low"].iloc[-1] > df_1m["high"].iloc[-3]
            bearish_fvg = df_1m["high"].iloc[-1] < df_1m["low"].iloc[-3]

            decision = "HOLD"
            trade_params = {}

            # --- 3. BULLISH SETUP ---
            if recent_low_sweep and bullish_fvg:
                decision = "BUY"
                entry = current_close
                sl = entry - (atr * 1.8)
                tp = entry + (abs(entry - sl) * 2.2)
                trade_params = {"entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2)}

            # --- 4. BEARISH SETUP ---
            elif recent_high_sweep and bearish_fvg:
                decision = "SELL"
                entry = current_close
                sl = entry + (atr * 1.8)
                tp = entry - (abs(entry - sl) * 2.2)
                trade_params = {"entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2)}

            return {"decision": decision, "trade_params": trade_params, "reason": "SMC Lookback Sweep & FVG Met"}

        except Exception as e:
            return {"decision": "HOLD", "reason": f"Error in engine: {str(e)}"}