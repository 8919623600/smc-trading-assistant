import pandas as pd
import numpy as np

class AdvancedSMCEngine:
    def __init__(self, min_rr=2.0, max_rr=8.0):
        self.min_rr = min_rr
        self.max_rr = max_rr
        self.active_setups = {}

    def calculate_atr(self, df, period=14):
        if len(df) < period:
            return 0.0005
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return float(tr.rolling(period).mean().iloc[-1])

    def check_fvg(self, df_15m, bias):
        if len(df_15m) < 3:
            return False
        c1_high = float(df_15m.iloc[-3]['high'])
        c3_low = float(df_15m.iloc[-1]['low'])
        c1_low = float(df_15m.iloc[-3]['low'])
        c3_high = float(df_15m.iloc[-1]['high'])

        if bias == "BULLISH" and c3_low > c1_high:
            return True
        if bias == "BEARISH" and c3_high < c1_low:
            return True
        return False

    def check_bos_choch(self, df_15m, direction):
        if len(df_15m) < 15:
            return True 
        
        recent_high = float(df_15m['high'].tail(15).max())
        recent_low = float(df_15m['low'].tail(15).min())
        current_close = float(df_15m.iloc[-1]['close'])

        if direction == "BUY" and current_close > recent_high * 0.999:
            return True 
        if direction == "SELL" and current_close < recent_low * 1.001:
            return True 
        return False

    def get_macro_external_liquidity(self, df_1h, bias):
        """Identifies deep external macro swing liquidity pools (e.g., 4325 type major lows/highs)"""
        if len(df_1h) < 50:
            return float(df_1h['low'].min()) if bias == "BULLISH" else float(df_1h['high'].max())
        
        # Look across a wider historical window for external range liquidity
        if bias == "BULLISH":
            # Find major macro low (External Sell-Side Liquidity)
            external_low = float(df_1h['low'].tail(50).min())
            return external_low
        else:
            # Find major macro high (External Buy-Side Liquidity)
            external_high = float(df_1h['high'].tail(50).max())
            return external_high

    def get_opposing_liquidity_targets(self, df_1h, direction, entry):
        """Targets opposing macro liquidity pools (e.g., Weak Highs / External Highs)"""
        highs = df_1h['high'].tail(50).values
        lows = df_1h['low'].tail(50).values

        if direction == "BUY":
            above_entry = [h for h in highs if h > entry]
            if not above_entry:
                tp1, tp2, tp3 = entry + 0.0050, entry + 0.0100, entry + 0.0150
            else:
                sorted_highs = sorted(list(set(above_entry)))
                tp1 = sorted_highs[0]
                tp2 = sorted_highs[len(sorted_highs)//2] if len(sorted_highs) > 1 else tp1 + 0.0050
                tp3 = sorted_highs[-1] # Target the major Weak High / External liquidity pool
        else:
            below_entry = [l for l in lows if l < entry]
            if not below_entry:
                tp1, tp2, tp3 = entry - 0.0050, entry - 0.0100, entry - 0.0150
            else:
                sorted_lows = sorted(list(set(below_entry)), reverse=True)
                tp1 = sorted_lows[0]
                tp2 = sorted_lows[len(sorted_lows)//2] if len(sorted_lows) > 1 else tp1 - 0.0050
                tp3 = sorted_lows[-1] # Target major external low liquidity

        return round(tp1, 5), round(tp2, 5), round(tp3, 5)

    def calculate_pnl_matrix(self, symbol, entry, sl, tp1, tp2):
        risk_pips = abs(entry - sl)
        if "EUR" in symbol or "USD" in symbol:
            risk_pips_display = risk_pips * 10000 if risk_pips < 1.0 else risk_pips
            tp1_pips_display = abs(tp1 - entry) * 10000 if abs(tp1 - entry) < 1.0 else abs(tp1 - entry)
            tp2_pips_display = abs(tp2 - entry) * 10000 if abs(tp2 - entry) < 1.0 else abs(tp2 - entry)
        else:
            risk_pips_display = risk_pips * 10
            tp1_pips_display = abs(tp1 - entry) * 10
            tp2_pips_display = abs(tp2 - entry) * 10

        lot_sizes = [0.01, 0.02, 0.03, 0.1, 0.2, 0.5, 1.0]
        matrix = []
        for lot in lot_sizes:
            dollar_per_pip = lot * 10.0
            matrix.append({
                "lot": lot,
                "loss": round(risk_pips_display * dollar_per_pip, 2),
                "tp1": round(tp1_pips_display * dollar_per_pip, 2),
                "tp2": round(tp2_pips_display * dollar_per_pip, 2)
            })
        return matrix, round(risk_pips_display, 1)

    def analyze(self, tf_data, symbol):
        df_4h = tf_data.get("4H")
        df_1h = tf_data.get("1H")
        df_15m = tf_data.get("15M")
        df_1m = tf_data.get("1M")

        if df_4h is None or df_1h is None or df_15m is None or df_1m is None:
            return {"status": "HOLD", "reason": "Missing multi-timeframe data feed"}

        # --- 1. 4H MACRO STRUCTURE BIAS ---
        swings_high = df_4h['high'].tail(10)
        swings_low = df_4h['low'].tail(10)
        is_higher_high = swings_high.iloc[-2] > swings_high.iloc[-5]
        is_higher_low = swings_low.iloc[-2] > swings_low.iloc[-5]
        bias = "BULLISH" if (is_higher_high and is_higher_low) else "BEARISH"

        # --- 2. MACRO EXTERNAL LIQUIDITY SWEEP CHECK ---
        historical_1h = df_1h.iloc[:-1]
        macro_liq_level = self.get_macro_external_liquidity(historical_1h, bias)
        current_1h_price = float(df_1h.iloc[-1]['close'])
        current_1h_low = float(df_1h.iloc[-1]['low'])
        current_1h_high = float(df_1h.iloc[-1]['high'])

        liquidity_swept = False
        if bias == "BULLISH" and current_1h_low <= macro_liq_level:
            liquidity_swept = True
        elif bias == "BEARISH" and current_1h_high >= macro_liq_level:
            liquidity_swept = True

        current_price = float(df_1m.iloc[-1]['close'])

        # Check existing active setup invalidation
        if symbol in self.active_setups:
            setup = self.active_setups[symbol]
            if (setup['direction'] == "BUY" and current_price < setup['sl']) or \
               (setup['direction'] == "SELL" and current_price > setup['sl']) or \
               setup['bias'] != bias:
                
                del self.active_setups[symbol]
                return {
                    "status": "INVALIDATED",
                    "symbol": symbol,
                    "reason": f"Price breached SL or macro structure flipped from {setup['bias']}."
                }

        # --- 3. SETUP FORMING & FVG + BOS VALIDATION ---
        if liquidity_swept and symbol not in self.active_setups:
            direction = "BUY" if bias == "BULLISH" else "SELL"
            
            has_imbalance = self.check_fvg(df_15m, bias)
            structure_confirmed = self.check_bos_choch(df_15m, direction)

            if not (has_imbalance and structure_confirmed):
                return {
                    "status": "HOLD",
                    "reason": f"Macro External Liquidity Swept at {macro_liq_level:.2f}, awaiting 15M FVG & BOS confirmation."
                }

            poi_level = float(df_15m['low'].tail(3).min()) if bias == "BULLISH" else float(df_15m['high'].tail(3).max())
            
            atr_1m = self.calculate_atr(df_1m)
            sl_buffer = atr_1m * 0.5
            recent_1m_swing = float(df_1m['low'].tail(5).min()) if bias == "BULLISH" else float(df_1m['high'].tail(5).max())
            sl = (recent_1m_swing - sl_buffer) if bias == "BULLISH" else (recent_1m_swing + sl_buffer)
            
            self.active_setups[symbol] = {
                "bias": bias,
                "direction": direction,
                "poi_price": poi_level,
                "sl": sl
            }

            p_fmt = f"{poi_level:.5f}" if "EUR" in symbol or "USD" in symbol else f"{poi_level:.2f}"
            return {
                "status": "SETUP_FORMING",
                "symbol": symbol,
                "direction": direction,
                "reason": f"Bias: {bias} | Macro Liquidity Swept [{macro_liq_level:.2f}] + 15M BOS Confirmed | Awaiting Order Block: {p_fmt}"
            }

        # --- 4. ACTIVE SETUP TRACKING & OPPOSING LIQUIDITY TP TARGETS ---
        if symbol in self.active_setups:
            setup = self.active_setups[symbol]
            direction = setup['direction']
            poi_level = setup['poi_price']
            p_fmt = f"{poi_level:.5f}" if "EUR" in symbol or "USD" in symbol else f"{poi_level:.2f}"
            
            entry = current_price
            sl = setup['sl']
            
            # Target Opposing Macro External Liquidity Pools (e.g., Weak Highs)
            tp1, tp2, tp3 = self.get_opposing_liquidity_targets(df_1h, direction, entry)
            
            risk_dist = abs(entry - sl)
            reward_dist = abs(tp1 - entry)
            rr = reward_dist / risk_dist if risk_dist > 0 else 0

            if self.min_rr <= rr <= self.max_rr:
                pnl_matrix, pips_risk = self.calculate_pnl_matrix(symbol, entry, sl, tp1, tp2)
                del self.active_setups[symbol]

                return {
                    "status": "TRIGGERED",
                    "decision": direction,
                    "reason": f"Execution confirmed inside Order Block (POI: {p_fmt}) targeting opposing liquidity.",
                    "trade_params": {
                        "entry": round(entry, 5),
                        "sl": round(sl, 5),
                        "tp1": tp1,
                        "tp2": tp2,
                        "tp3": tp3,
                        "rr": round(rr, 2),
                        "pips_risk": pips_risk,
                        "pnl_matrix": pnl_matrix
                    }
                }
            else:
                curr_fmt = f"{current_price:.5f}" if "EUR" in symbol or "USD" in symbol else f"{current_price:.2f}"
                return {
                    "status": "HOLD", 
                    "reason": f"External Liquidity Swept | Awaiting price to reach Order Block ({p_fmt}) | Current RR: {rr:.2f}"
                }

        # Default HOLD reason
        curr_fmt = f"{current_price:.5f}" if "EUR" in symbol or "USD" in symbol else f"{current_price:.2f}"
        return {
            "status": "HOLD", 
            "reason": f"Awaiting Macro External Liquidity Sweep [{macro_liq_level:.2f}] | Bias: {bias} | Current Price: {curr_fmt}"
        }