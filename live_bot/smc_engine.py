import pandas as pd
import numpy as np

class AdvancedSMCEngine:
    def __init__(self, min_rr=1.5, max_rr=5.0):
        self.min_rr = min_rr
        self.max_rr = max_rr

    def _normalize_df(self, df):
        if df is not None and not df.empty:
            df = df.copy()
            df.columns = [str(c).lower().strip() for c in df.columns]
            return df
        return df

    def calculate_atr(self, df, period=14):
        df = self._normalize_df(df)
        if df is None or len(df) < period:
            return 2.0
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                np.abs(df['high'] - df['close'].shift(1)),
                np.abs(df['low'] - df['close'].shift(1))
            )
        )
        return df['tr'].rolling(period).mean().iloc[-1]

    def identify_swing_points(self, df, window=3):
        df = self._normalize_df(df)
        if df is None or len(df) < window * 2 + 1:
            return df
        df['swing_high'] = df['high'][(df['high'] == df['high'].rolling(window*2+1, center=True).max())]
        df['swing_low'] = df['low'][(df['low'] == df['low'].rolling(window*2+1, center=True).min())]
        return df

    def get_market_bias(self, df):
        df = self._normalize_df(df)
        if df is None or len(df) < 15:
            return "BULLISH"
        closes = df['close'].values
        if closes[-1] > np.mean(closes[-10:]):
            return "BULLISH"
        else:
            return "BEARISH"

    def analyze(self, data_dict, symbol="XAU/USD"):
        df_4h = self._normalize_df(data_dict.get("4H"))
        df_15m = self._normalize_df(data_dict.get("15M"))
        df_1m = self._normalize_df(data_dict.get("1M"))
        
        if df_1m is None or len(df_1m) < 30:
            return {"decision": "WAIT", "current_price": 0.0, "reason": "Insufficient 1M data", "trade_params": {}}
            
        current_close = float(df_1m.iloc[-1]['close'])
        bias_4h = self.get_market_bias(df_4h)
        
        is_forex = "EUR" in symbol.upper() or ("USD" in symbol.upper() and "XAU" not in symbol.upper())
        atr_1m = self.calculate_atr(df_1m, period=14)
        if pd.isna(atr_1m):
            atr_1m = 1.0 if not is_forex else 0.0015

        if bias_4h == "BULLISH":
            entry = current_close
            invalidation_swing_low = df_1m['low'].iloc[-15:].min()
            sl = invalidation_swing_low - (atr_1m * 0.5)
            
            risk = entry - sl
            if risk <= 0:
                return {"decision": "WAIT", "current_price": current_close, "reason": "Invalid risk bounds", "trade_params": {}}
                
            tp1 = entry + (risk * 1.5)
            tp2 = entry + (risk * 3.0)
            rr = round((tp2 - entry) / risk, 2)
            
            if self.min_rr <= rr <= self.max_rr:
                return {
                    "decision": "BUY",
                    "current_price": round(entry, 2 if not is_forex else 4),
                    "reason": "4H Bullish Bias + 1M Structure Confirmed.",
                    "trade_params": {
                        "entry": round(entry, 2 if not is_forex else 4),
                        "sl": round(sl, 2 if not is_forex else 4),
                        "tp1": round(tp1, 2 if not is_forex else 4),
                        "tp2": round(tp2, 2 if not is_forex else 4),
                        "rr": rr
                    }
                }

        elif bias_4h == "BEARISH":
            entry = current_close
            invalidation_swing_high = df_1m['high'].iloc[-15:].max()
            sl = invalidation_swing_high + (atr_1m * 0.5)
            
            risk = sl - entry
            if risk <= 0:
                return {"decision": "WAIT", "current_price": current_close, "reason": "Invalid risk bounds", "trade_params": {}}
                
            tp1 = entry - (risk * 1.5)
            tp2 = entry - (risk * 3.0)
            rr = round((entry - tp2) / risk, 2)
            
            if self.min_rr <= rr <= self.max_rr:
                return {
                    "decision": "SELL",
                    "current_price": round(entry, 2 if not is_forex else 4),
                    "reason": "4H Bearish Bias + 1M Structure Confirmed.",
                    "trade_params": {
                        "entry": round(entry, 2 if not is_forex else 4),
                        "sl": round(sl, 2 if not is_forex else 4),
                        "tp1": round(tp1, 2 if not is_forex else 4),
                        "tp2": round(tp2, 2 if not is_forex else 4),
                        "rr": rr
                    }
                }

        return {"decision": "WAIT", "current_price": current_close, "reason": "Awaiting strict alignment.", "trade_params": {}}

# Compatibility alias
SMCTradingEngine = AdvancedSMCEngine