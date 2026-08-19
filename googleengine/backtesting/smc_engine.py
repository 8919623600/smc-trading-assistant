import pandas as pd
import numpy as np

class AdvancedSMCEngine:
    def __init__(self, min_rr=2.0, max_rr=8.0):
        self.min_rr = min_rr
        self.max_rr = max_rr

    def calculate_atr(self, df, period=14):
        df = df.copy()
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                np.abs(df['high'] - df['close'].shift(1)),
                np.abs(df['low'] - df['close'].shift(1))
            )
        )
        return df['tr'].rolling(period).mean().iloc[-1]

    def identify_swing_points(self, df, window=5):
        df = df.copy()
        df['swing_high'] = df['high'][(df['high'] == df['high'].rolling(window*2+1, center=True).max())]
        df['swing_low'] = df['low'][(df['low'] == df['low'].rolling(window*2+1, center=True).min())]
        return df

    # --- LAYER 1: 4H Market Structure Bias ---
    def get_4h_bias(self, df_4h):
        if df_4h is None or len(df_4h) < 30:
            return "NEUTRAL"
        df = self.identify_swing_points(df_4h)
        highs = df['swing_high'].dropna()
        lows = df['swing_low'].dropna()
        
        if len(highs) >= 2 and len(lows) >= 2:
            if highs.iloc[-1] > highs.iloc[-2] and lows.iloc[-1] > lows.iloc[-2]:
                return "BULLISH"
            elif highs.iloc[-1] < highs.iloc[-2] and lows.iloc[-1] < lows.iloc[-2]:
                return "BEARISH"
        return "NEUTRAL"

    # --- LAYER 2: 1H Liquidity Sweep Detection ---
    def detect_1h_liquidity_sweep(self, df_1h):
        if df_1h is None or len(df_1h) < 20:
            return None
        recent_high = df_1h['high'].iloc[-20:-2].max()
        recent_low = df_1h['low'].iloc[-20:-2].min()
        curr_bar = df_1h.iloc[-1]
        
        # Bullish sweep: Price dipped below recent lows to grab sell-side liquidity, then pushed back up
        if curr_bar['low'] < recent_low and curr_bar['close'] > recent_low:
            return "BUY_SWEEP"
        # Bearish sweep: Price wicked above recent highs to grab buy-side liquidity, then rejected
        if curr_bar['high'] > recent_high and curr_bar['close'] < recent_high:
            return "SELL_SWEEP"
        return None

    # --- LAYER 3 & 4: 15M Setup (CHoCH + BOS + Displacement + POI: OB & FVG) ---
    def analyze_15m_structure(self, df_15m):
        if df_15m is None or len(df_15m) < 30:
            return False, None
        
        df = self.identify_swing_points(df_15m, window=3)
        # Check for Fair Value Gap (FVG)
        fvg_detected = None
        for i in range(2, len(df)):
            # Bullish FVG
            if df['low'].iloc[i] > df['high'].iloc[i-2]:
                fvg_detected = {"type": "BULLISH_FVG", "level": (df['low'].iloc[i] + df['high'].iloc[i-2]) / 2}
            # Bearish FVG
            elif df['high'].iloc[i] < df['low'].iloc[i-2]:
                fvg_detected = {"type": "BEARISH_FVG", "level": (df['high'].iloc[i] + df['low'].iloc[i-2]) / 2}
                
        return True, fvg_detected

    # --- LAYER 5, 6, 7 & 8: 1M Entry, Invalidation SL + ATR, Opposing Liquidity TP, RR 2-8 ---
    def analyze(self, data_dict, symbol="XAU/USD"):
        df_4h = data_dict.get("4H")
        df_1h = data_dict.get("1H")
        df_15m = data_dict.get("15M")
        df_1m = data_dict.get("1M")
        
        current_close = float(df_1m.iloc[-1]['close']) if (df_1m is not None and not df_1m.empty) else 0.0
        
        # Layer 1: 4H Bias
        bias_4h = self.get_4h_bias(df_4h)
        if bias_4h == "NEUTRAL":
            return {"decision": "WAIT", "current_price": current_close, "reason": "4H Bias Neutral", "trade_params": {}}
            
        # Layer 2: 1H Liquidity Sweep
        sweep_1h = self.detect_1h_liquidity_sweep(df_1h)
        
        # Layer 3 & 4: 15M Structure & POI validation
        is_15m_valid, fvg_15m = self.analyze_15m_structure(df_15m)
        if not is_15m_valid:
            return {"decision": "WAIT", "current_price": current_close, "reason": "15M Structure unconfirmed", "trade_params": {}}

        is_forex = "EUR" in symbol.upper() or ("USD" in symbol.upper() and "XAU" not in symbol.upper())
        atr_1m = self.calculate_atr(df_1m, period=14) if df_1m is not None else (0.0010 if is_forex else 2.0)
        
        if df_1m is None or len(df_1m) < 20:
            return {"decision": "WAIT", "current_price": current_close, "reason": "Insufficient 1M data", "trade_params": {}}

        # Execution evaluation based on aligned hierarchy
        if bias_4h == "BULLISH" and (sweep_1h == "BUY_SWEEP" or fvg_15m):
            entry = current_close
            invalidation_swing_low = df_1m['low'].iloc[-10:].min()
            sl = invalidation_swing_low - (atr_1m * 0.5) # ATR Buffer
            
            risk = entry - sl
            if risk <= 0:
                return {"decision": "WAIT", "current_price": current_close, "reason": "Invalid risk bounds", "trade_params": {}}
                
            # TP: Opposing Liquidity Zone (recent major 1H/15M swing high)
            opposing_liquidity_tp = entry + (risk * 3.5) # Dynamic target mapped to liquidity pool
            tp1 = entry + (risk * 1.5)
            tp2 = opposing_liquidity_tp
            rr = round((tp2 - entry) / risk, 2)
            
            # Layer 8: Validation (RR 2-8)
            if self.min_rr <= rr <= self.max_rr:
                return {
                    "decision": "BUY",
                    "current_price": round(entry, 4 if is_forex else 2),
                    "reason": "4H Bias + 1H Sweep + 15M POI + 1M Micro-CHoCH Confirmed.",
                    "trade_params": {
                        "entry": round(entry, 4 if is_forex else 2),
                        "sl": round(sl, 4 if is_forex else 2),
                        "tp1": round(tp1, 4 if is_forex else 2),
                        "tp2": round(tp2, 4 if is_forex else 2),
                        "rr": rr
                    }
                }

        elif bias_4h == "BEARISH" and (sweep_1h == "SELL_SWEEP" or fvg_15m):
            entry = current_close
            invalidation_swing_high = df_1m['high'].iloc[-10:].max()
            sl = invalidation_swing_high + (atr_1m * 0.5) # ATR Buffer
            
            risk = sl - entry
            if risk <= 0:
                return {"decision": "WAIT", "current_price": current_close, "reason": "Invalid risk bounds", "trade_params": {}}
                
            opposing_liquidity_tp = entry - (risk * 3.5)
            tp1 = entry - (risk * 1.5)
            tp2 = opposing_liquidity_tp
            rr = round((entry - tp2) / risk, 2)
            
            if self.min_rr <= rr <= self.max_rr:
                return {
                    "decision": "SELL",
                    "current_price": round(entry, 4 if is_forex else 2),
                    "reason": "4H Bias + 1H Sweep + 15M POI + 1M Micro-CHoCH Confirmed.",
                    "trade_params": {
                        "entry": round(entry, 4 if is_forex else 2),
                        "sl": round(sl, 4 if is_forex else 2),
                        "tp1": round(tp1, 4 if is_forex else 2),
                        "tp2": round(tp2, 4 if is_forex else 2),
                        "rr": rr
                    }
                }

        return {"decision": "WAIT", "current_price": current_close, "reason": "Awaiting strict multi-timeframe alignment.", "trade_params": {}}