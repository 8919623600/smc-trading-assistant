import pandas as pd
import numpy as np

class AdvancedSMCEngine:
    def __init__(self, min_rr=2.0, max_rr=8.0):
        self.min_rr = min_rr
        self.max_rr = max_rr
        self.active_setups = {}

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

        # --- 1. 4H BIAS CHECK ---
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
                    "reason": f"Price breached SL or macro bias flipped from {setup['bias']}."
                }

        # --- 3. SETUP FORMING (Advance Notice) ---
        if liquidity_swept and symbol not in self.active_setups:
            direction = "BUY" if bias == "BULLISH" else "SELL"
            recent_1m_swing = float(df_1m['low'].tail(5).min()) if bias == "BULLISH" else float(df_1m['high'].tail(5).max())
            sl = recent_1m_swing - 0.0005 if bias == "BULLISH" else recent_1m_swing + 0.0005
            
            self.active_setups[symbol] = {
                "bias": bias,
                "direction": direction,
                "poi_price": current_price,
                "sl": sl
            }

            return {
                "status": "SETUP_FORMING",
                "symbol": symbol,
                "direction": direction,
                "reason": f"4H Bias: {bias} | 1H {sweep_type} | Monitoring 1M triggers."
            }

        # --- 4. FINAL TRIGGER ---
        if symbol in self.active_setups:
            setup = self.active_setups[symbol]
            direction = setup['direction']
            
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
                    "reason": f"1M CHoCH confirmed inside POI.",
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
                return {"status": "HOLD", "reason": f"Active setup tracking, awaiting valid RR (Current RR: {rr:.2f})"}

        # Dynamic target level display based on 4H bias
        target_level = recent_1h_high if bias == "BEARISH" else recent_1h_low
        target_label = "1H High (EQH)" if bias == "BEARISH" else "1H Low (EQL)"
        fmt_target = f"{target_level:.5f}" if "EUR" in symbol or "USD" in symbol else f"{target_level:.2f}"

        return {
            "status": "HOLD", 
            "reason": f"Awaiting 1H Liquidity Sweep | Bias: {bias} | Target Level [{target_label}]: {fmt_target}"
        }