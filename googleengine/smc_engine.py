import pandas as pd
import numpy as np

class SMCTradingEngine:
    def __init__(self, min_rr=1.5, max_rr=10.0, backtest_mode=True):
        self.min_rr = min_rr
        self.max_rr = max_rr
        self.backtest_mode = backtest_mode

    def analyze(self, data_dict):
        try:
            df_4h = data_dict.get("4H")
            df_1h = data_dict.get("1H")
            df_15m = data_dict.get("15M")
            df_1m_raw = data_dict.get("1M")

            if df_1m_raw is None or len(df_1m_raw) < 50 or df_1h is None or len(df_1h) < 20 or df_15m is None or len(df_15m) < 20:
                return {"decision": "HOLD", "reason": "Insufficient data"}

            df_1m = df_1m_raw.copy()

            current_bar = df_1m.iloc[-1]
            current_close = current_bar["close"]

            # --- 1. HIGHER TIMEFRAME (1H) TREND BIAS ---
            df_1h["sma_20"] = df_1h["close"].rolling(20).mean()
            htf_bullish = df_1h["close"].iloc[-1] > df_1h["sma_20"].iloc[-1]

            # --- 2. CALCULATE ATR FOR INITIAL SL ---
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

            # Volatility Noise Check
            mean_atr = df_1m["atr"].rolling(50).mean().iloc[-1]
            if not pd.isna(mean_atr) and atr > (mean_atr * 2.0):
                return {"decision": "HOLD", "reason": "High Volatility Spike / Noise Filter Active"}

            # --- 3. SMC STRUCTURE WITH LOOKBACK WINDOW ---
            recent_high = df_1m["high"].iloc[-25:-3].max()
            recent_low = df_1m["low"].iloc[-25:-3].min()

            recent_low_sweep = df_1m["low"].iloc[-3:].min() <= recent_low
            recent_high_sweep = df_1m["high"].iloc[-3:].max() >= recent_high

            bullish_fvg = df_1m["low"].iloc[-1] > df_1m["high"].iloc[-3]
            bearish_fvg = df_1m["high"].iloc[-1] < df_1m["low"].iloc[-3]

            decision = "HOLD"
            trade_params = {}

            # --- 4. CONDITIONAL EXECUTION BASED ON HTF TREND ---
            if htf_bullish and recent_low_sweep and bullish_fvg:
                decision = "BUY"
                entry = current_close
                sl = entry - (atr * 1.8)
                # Initial placeholder TP, will be dynamically managed by trailing structure
                tp = entry + (abs(entry - sl) * 5.0) 
                trade_params = {"entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2)}

            elif not htf_bullish and recent_high_sweep and bearish_fvg:
                decision = "SELL"
                entry = current_close
                sl = entry + (atr * 1.8)
                tp = entry - (abs(entry - sl) * 5.0)
                trade_params = {"entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2)}

            return {"decision": decision, "trade_params": trade_params, "reason": "HTF Aligned SMC Setup + Structure Trailing Ready"}

        except Exception as e:
            return {"decision": "HOLD", "reason": f"Error in engine: {str(e)}"}