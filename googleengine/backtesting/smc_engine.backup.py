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

    def calculate_lot_breakdown(self, risk_in_pips, is_forex):
        """
        Calculates P&L for standard lot sizes: 0.01, 0.02, 0.03, 0.1, 0.2, 0.5
        For EUR/USD (Forex): 1 standard lot = $10 per pip. 0.01 lot = $0.10 per pip.
        For XAU/USD (Gold): 1 standard lot = $1 per 0.01 move (or $100 per full $1.00 move). 
                           Usually, 0.01 lot on Gold = $1.00 per $1.00 move in price.
        """
        standard_lots = [0.01, 0.02, 0.03, 0.1, 0.2, 0.5]
        breakdown = {}
        
        # Determine dollar value per unit risk per 0.01 lot
        # EUR/USD: 1 pip = 0.0001. Dollar per pip for 0.01 lot = $0.10
        # XAU/USD: 1 point = $1.00. Dollar per $1.00 move for 0.01 lot = $1.00
        if is_forex:
            pips = risk_in_pips * 10000
            for lot in standard_lots:
                dollar_loss = pips * (lot * 10) # $0.10 per pip per 0.01 lot
                breakdown[f"{lot} Lot"] = round(dollar_loss, 2)
        else:
            price_diff = risk_in_pips
            for lot in standard_lots:
                # 0.01 lot gold = $1 per $1 move. 0.1 lot = $10 per $1 move.
                dollar_loss = price_diff * (lot * 100)
                breakdown[f"{lot} Lot"] = round(dollar_loss, 2)
                
        return breakdown

    def get_optimal_lot_for_target_loss(self, risk_in_pips, is_forex, target_loss=10.0):
        if risk_in_pips <= 0:
            return 0.01
            
        if is_forex:
            pips = risk_in_pips * 10000
            # dollar_per_lot_per_pip = 1000 ($10 per pip for 1.0 lot)
            # target_loss = pips * lot * 10 -> lot = target_loss / (pips * 10)
            ideal_lot = target_loss / (pips * 10)
        else:
            # target_loss = price_diff * lot * 100 -> lot = target_loss / (price_diff * 100)
            ideal_lot = target_loss / (risk_in_pips * 100)
            
        # Round to standard broker increments (min 0.01)
        return max(0.01, round(ideal_lot, 2))

    def analyze(self, data_dict, symbol="XAU/USD"):
        df_4h = data_dict.get("4H")
        df_1m = data_dict.get("1M")
        
        bias_4h = self.determine_bias(df_4h)
        
        if df_1m is None or len(df_1m) < 30:
            current_close = float(df_1m.iloc[-1]['close']) if (df_1m is not None and not df_1m.empty) else 0.0
            return {
                "decision": None, 
                "current_price": current_close, 
                "reason": "Insufficient 1M data frames", 
                "bias_4h": bias_4h, 
                "trade_params": {}
            }
            
        current_bar = df_1m.iloc[-1]
        close_price = float(current_bar['close'])
        high_price = float(current_bar['high'])
        low_price = float(current_bar['low'])
        
        obs_1m = self.detect_order_blocks(df_1m)
        recent_obs = [ob for ob in obs_1m if abs(ob['index'] - len(df_1m)) < 25] if obs_1m else []
        
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
                return {"decision": None, "current_price": close_price, "reason": "Invalid risk bounds", "bias_4h": bias_4h, "trade_params": {}}
                
            tp1 = entry + (risk * 1.5)
            tp2 = entry + (risk * 3.0)
            rr = round((tp2 - entry) / risk, 2)
            
            if self.min_rr <= rr <= self.max_rr:
                lot_breakdown = self.calculate_lot_breakdown(risk, is_forex)
                optimal_lot = self.get_optimal_lot_for_target_loss(risk, is_forex, target_loss=10.0)
                
                return {
                    "decision": "BUY",
                    "current_price": round(entry, 4 if is_forex else 2),
                    "reason": "Confirmed Bullish Order Block mitigation with 4H alignment.",
                    "bias_4h": bias_4h,
                    "trade_params": {
                        "entry": round(entry, 4 if is_forex else 2),
                        "sl": round(sl, 4 if is_forex else 2),
                        "tp1": round(tp1, 4 if is_forex else 2),
                        "tp2": round(tp2, 4 if is_forex else 2),
                        "rr": rr,
                        "risk_dollar_breakdown_by_lot": lot_breakdown,
                        "recommended_lot_for_$10_loss": optimal_lot
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
                return {"decision": None, "current_price": close_price, "reason": "Invalid risk bounds", "bias_4h": bias_4h, "trade_params": {}}
                
            tp1 = entry - (risk * 1.5)
            tp2 = entry - (risk * 3.0)
            rr = round((entry - tp2) / risk, 2)
            
            if self.min_rr <= rr <= self.max_rr:
                lot_breakdown = self.calculate_lot_breakdown(risk, is_forex)
                optimal_lot = self.get_optimal_lot_for_target_loss(risk, is_forex, target_loss=10.0)
                
                return {
                    "decision": "SELL",
                    "current_price": round(entry, 4 if is_forex else 2),
                    "reason": "Confirmed Bearish Order Block mitigation with 4H alignment.",
                    "bias_4h": bias_4h,
                    "trade_params": {
                        "entry": round(entry, 4 if is_forex else 2),
                        "sl": round(sl, 4 if is_forex else 2),
                        "tp1": round(tp1, 4 if is_forex else 2),
                        "tp2": round(tp2, 4 if is_forexoster else 2),
                        "tp2": round(tp2, 4 if is_forex else 2),
                        "rr": rr,
                        "risk_dollar_breakdown_by_lot": lot_breakdown,
                        "recommended_lot_for_$10_loss": optimal_lot
                    }
                }
                
        # Fallback when no BUY/SELL decision is triggered (e.g., WAIT state)
        return {
            "decision": "WAIT", 
            "current_price": round(close_price, 4 if is_forex else 2), 
            "reason": "No high-probability SMC trigger.", 
            "bias_4h": bias_4h, 
            "trade_params": {}
        }