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
        """Validates if a 3-candle Fair Value Gap exists matching structural bias"""
        if len(df_15m) < 3:
            return False
        c1_high = float(df_15m.iloc[-3]['high'])
        c3_low = float(df_15m.iloc[-1]['low'])
        c1_low = float(df_15m.iloc[-3]['low'])
        c3_high = float(df_15m.iloc[-1]['high'])

        if bias == "BULLISH" and c3_low > c1_high:
            return True # Bullish FVG imbalance
        if bias == "BEARISH" and c3_high < c1_low:
            return True # Bearish FVG imbalance
        return False

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

        # --- 2. 1H LIQUIDITY SWEEP CHECK (Excluding Active Candle) ---
        historical_1h = df_1h.iloc[:-1]
        recent_1h_high = float(historical_1h['high'].tail(15).max())
        recent_1h_low = float(historical_1h['low'].tail(15).min())
        
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

        # --- 3. SETUP FORMING & FVG / ORDER BLOCK VALIDATION ---
        if liquidity_swept and symbol not in self.active_setups:
            direction = "BUY" if bias == "BULLISH" else "SELL"
            
            # Require 15M FVG Confluence
            has_imbalance = self.check_fvg(df_15m, bias)
            if not has_imbalance:
                return {
                    "status": "HOLD",
                    "reason": f"1H {sweep_type} detected, but waiting for valid 15M FVG/Imbalance confirmation."
                }

            poi_level = float(df_15m['low'].tail(3).min()) if bias == "BULLISH" else float(df_15m['high'].tail(3).max())
            
            # Apply ATR Buffer to Stop Loss
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
                "reason": f"4H Bias: {bias} | 1H {sweep_type} + 15M FVG Confirmed | Awaiting price to reach Order Block: {p_fmt}"
            }

        # --- 4. ACTIVE SETUP TRACKING & TRIGGER ---
        if symbol in self.active_setups:
            setup = self.active_setups[symbol]
            direction = setup['direction']
            poi_level = setup['poi_price']
            p_fmt = f"{poi_level:.5f}" if "EUR" in symbol or "USD" in symbol else f"{poi_level:.2f}"
            
            entry = current_price
            sl = setup['sl']
            tp1 = entry + (abs(entry - sl) * 3.0) if direction == "BUY" else entry - (abs(sl - entry) * 3.0)
            tp2 = entry + (abs(entry - sl) * 6.0) if direction == "BUY" else entry - (abs(sl - entry) * 6.0)
            rr = abs(tp1 - entry) / abs(entry - sl)

            if self.min_rr <= rr <= self.max_rr:
                pnl_matrix, pips_risk = self.calculate_pnl_matrix(symbol, entry, sl, tp1, tp2)
                del self.active_setups[symbol]

                return {
                    "status": "TRIGGERED",
                    "decision": direction,
                    "reason": f"1M execution confirmed inside Order Block (POI: {p_fmt}) with ATR-buffered SL.",
                    "trade_params": {
                        "entry": round(entry, 5),
                        "sl": round(sl, 5),
                        "tp1": round(tp1, 5),
                        "tp2": round(tp2, 5),
                        "rr": round(rr, 2),
                        "pips_risk": pips_risk,
                        "pnl_matrix": pnl_matrix
                    }
                }
            else:
                curr_fmt = f"{current_price:.5f}" if "EUR" in symbol or "USD" in symbol else f"{current_price:.2f}"
                return {
                    "status": "HOLD", 
                    "reason": f"Sweep & FVG Validated | Awaiting price to reach Order Block ({p_fmt}) | Current Price: {curr_fmt}"
                }

        # Default HOLD reason
        target_str = f"{recent_1h_low:.5f}" if bias == "BULLISH" else f"{recent_1h_high:.5f}"
        target_name = "1H Low (EQL)" if bias == "BULLISH" else "1H High (EQH)"
        curr_fmt = f"{current_price:.5f}" if "EUR" in symbol or "USD" in symbol else f"{current_price:.2f}"
        return {
            "status": "HOLD", 
            "reason": f"Awaiting 1H Liquidity Sweep | Bias: {bias} | Target [{target_name}]: {target_str} | Current Price: {curr_fmt}"
        }