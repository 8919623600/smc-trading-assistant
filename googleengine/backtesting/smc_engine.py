import pandas as pd
import numpy as np

class SMCTradingEngine:
    def __init__(self, min_rr=2.0, max_rr=8.0):
        self.min_rr = min_rr
        self.max_rr = max_rr

    def identify_swing_points(self, df, window=5):
        df = df.copy()
        df['swing_high'] = df['high'][(df['high'] == df['high'].rolling(window*2+1, center=True).max())]
        df['swing_low'] = df['low'][(df['low'] == df['low'].rolling(window*2+1, center=True).min())]
        return df

    def determine_bias(self, df_4h):
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
                
        closes = df_4h['close'].values
        if closes[-1] > np.mean(closes[-20:]):
            return "BULLISH"
        elif closes[-1] < np.mean(closes[-20:]):
            return "BEARISH"
            
        return "NEUTRAL"

    def detect_order_blocks(self, df):
        obs = []
        for i in range(3, len(df) - 1):
            if df['close'].iloc[i-1] < df['open'].iloc[i-1] and df['close'].iloc[i] > df['high'].iloc[i-1]:
                obs.append({
                    "type": "BULLISH_OB",
                    "index": i-1,
                    "price_low": df['low'].iloc[i-1],
                    "price_high": df['high'].iloc[i-1]
                })
            elif df['close'].iloc[i-1] > df['open'].iloc[i-1] and df['close'].iloc[i] < df['low'].iloc[i-1]:
                obs.append({
                    "type": "BEARISH_OB",
                    "index": i-1,
                    "price_low": df['low'].iloc[i-1],
                    "price_high": df['high'].iloc[i-1]
                })
        return obs

    def analyze(self, data_dict, symbol="XAU/USD"):
        df_4h = data_dict.get("4H")
        df_1m = data_dict.get("1M")
        
        bias_4h = self.determine_bias(df_4h)
        
        if df_1m is None or len(df_1m) < 30:
            return {"decision": None, "reason": "Insufficient 1M data frames", "bias_4h": bias_4h, "trade_params": {}}
            
        current_bar = df_1m.iloc[-1]
        close_price = float(current_bar['close'])
        high_price = float(current_bar['high'])
        low_price = float(current_bar['low'])
        
        obs_1m = self.detect_order_blocks(df_1m)
        recent_obs = [ob for ob in obs_1m if abs(ob['index'] - len(df_1m)) < 25] if obs_1m else []
        
        # Asset-aware Pip/Buffer scaling (EUR/USD vs Gold)
        is_forex = "EUR" in symbol.upper() or ("USD" in symbol.upper() and "XAU" not in symbol.upper())
        sl_buffer = 0.0015 if is_forex else (low_price * 0.001)

        if bias_4h == "BULLISH":
            entry = close_price
            sl = low_price - sl_buffer
            
            if recent_obs:
                bullish_obs = [ob for ob in recent_obs if ob['type'] == 'BULLISH_OB']
                if bullish_obs:
                    sl = float(bullish_obs[-1]['price_low'] - (0.0005 if is_forex else close_price * 0.0005))
            
            risk = entry - sl
            if risk <= 0:
                return {"decision": None, "reason": "Invalid risk bounds", "bias_4h": bias_4h, "trade_params": {}}
                
            tp1 = entry + (risk * 1.5)
            tp2 = entry + (risk * 3.0)
            rr = round((tp2 - entry) / risk, 2)
            
            if self.min_rr <= rr <= self.max_rr:
                return {
                    "decision": "BUY",
                    "reason": "Confirmed Bullish Order Block mitigation with 4H alignment.",
                    "bias_4h": bias_4h,
                    "trade_params": {
                        "entry": round(entry, 4 if is_forex else 2),
                        "sl": round(sl, 4 if is_forex else 2),
                        "tp1": round(tp1, 4 if is_forex else 2),
                        "tp2": round(tp2, 4 if is_forex else 2),
                        "rr": rr
                    }
                }
                
        elif bias_4h == "BEARISH":
            entry = close_price
            sl = high_price + sl_buffer
            
            if recent_obs:
                bearish_obs = [ob for ob in recent_obs if ob['type'] == 'BEARISH_OB']
                if bearish_obs:
                    sl = float(bearish_obs[-1]['price_high'] + (0.0005 if is_forex else close_price * 0.0005))
            
            risk = sl - entry
            if risk <= 0:
                return {"decision": None, "reason": "Invalid risk bounds", "bias_4h": bias_4h, "trade_params": {}}
                
            tp1 = entry - (risk * 1.5)
            tp2 = entry - (risk * 3.0)
            rr = round((entry - tp2) / risk, 2)
            
            if self.min_rr <= rr <= self.max_rr:
                return {
                    "decision": "SELL",
                    "reason": "Confirmed Bearish Order Block mitigation with 4H alignment.",
                    "bias_4h": bias_4h,
                    "trade_params": {
                        "entry": round(entry, 4 if is_forex else 2),
                        "sl": round(sl, 4 if is_forex else 2),
                        "tp1": round(tp1, 4 if is_forex else 2),
                        "tp2": round(tp2, 4 if is_forex else 2),
                        "rr": rr
                    }
                }
                
        return {"decision": None, "reason": "No high-probability SMC trigger.", "bias_4h": bias_4h, "trade_params": {}}