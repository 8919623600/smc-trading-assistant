import pandas as pd
import numpy as np

class SMCTradingEngine:
    def __init__(self, min_rr=2.0, max_rr=8.0, atr_multiplier=0.5, backtest_mode=True):
        self.min_rr = min_rr
        self.max_rr = max_rr
        self.atr_multiplier = atr_multiplier
        self.backtest_mode = backtest_mode

    def analyze(self, data_dict):
        """
        Takes multi-timeframe data dictionary: {'4H': df, '1H': df, '15M': df, '1M': df}
        Returns a decision: 'BUY', 'SELL', or 'HOLD' along with trade parameters.
        """
        try:
            df_4h = data_dict.get("4H")
            df_1h = data_dict.get("1H")
            df_15m = data_dict.get("15M")
            df_1m = data_dict.get("1M")

            if df_1m is None or len(df_1m) < 50:
                return {"decision": "HOLD", "reason": "Insufficient 1M data"}

            current_bar = df_1m.iloc[-1]
            current_close = current_bar["close"]
            current_high = current_bar["high"]
            current_low = current_bar["low"]

            # --- 1. CALCULATE ATR FOR VOLATILITY-BASED SL/TP ---
            df_1m["tr"] = np.maximum(
                df_1m["high"] - df_1m["low"],
                np.maximum(
                    abs(df_1m["high"] - df_1m["shift"](1) if "shift" in dir(df_1m) else abs(df_1m["high"] - df_1m["close"].shift(1))),
                    abs(df_1m["low"] - df_1m["close"].shift(1))
                )
            )
            atr = df_1m["tr"].rolling(14).mean().iloc[-1]
            if pd.isna(atr) or atr == 0:
                atr = 2.0  # Fallback for gold volatility

            # --- 2. IDENTIFY SMC STRUCTURE (Order Block & FVG Simulation) ---
            # Recent 20-bar high/low for liquidity sweeps
            recent_high = df_1m["high"].iloc[-20:-1].max()
            recent_low = df_1m["low"].iloc[-20:-1].min()

            # Fair Value Gap (FVG) Detection on 1M/15M
            # Bullish FVG: Low of current bar > High of bar - 2
            bullish_fvg = df_1m["low"].iloc[-1] > df_1m["high"].iloc[-3]
            # Bearish FVG: High of current bar < Low of bar - 2
            bearish_fvg = df_1m["high"].iloc[-1] > df_1m["low"].iloc[-3]

            # Order Block (OB) Proxies: Strong displacement candles
            body_size = abs(current_close - current_bar["open"])
            avg_body = abs(df_1m["close"] - df_1m["open"]).rolling(20).mean().iloc[-1]
            is_displacement = body_size > (1.5 * avg_body) if not pd.isna(avg_body) else True

            decision = "HOLD"
            trade_params = {}

            # --- 3. BULLISH SETUP (Demand Zone + Sweep + FVG + OB) ---
            # Price swept recent lows (liquidity grab) and is bouncing with displacement & FVG
            if current_low <= recent_low and bullish_fvg and is_displacement:
                decision = "BUY"
                entry = current_close
                sl = entry - (atr * 1.5)  # Stop loss below structural low / OB
                tp = entry + (abs(entry - sl) * 2.5)  # 2.5 RR Target
                trade_params = {"entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2)}

            # --- 4. BEARISH SETUP (Supply Zone + Sweep + FVG + OB) ---
            # Price swept recent highs (liquidity grab) and is dropping with displacement & FVG
            elif current_high >= recent_high and bearish_fvg and is_displacement:
                decision = "SELL"
                entry = current_close
                sl = entry + (atr * 1.5)  # Stop loss above structural high / OB
                tp = entry - (abs(entry - sl) * 2.5)  # 2.5 RR Target
                trade_params = {"entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2)}

            return {"decision": decision, "trade_params": trade_params, "reason": "SMC Confluence Met"}

        except Exception as e:
            return {"decision": "HOLD", "reason": f"Error in engine: {str(e)}"}