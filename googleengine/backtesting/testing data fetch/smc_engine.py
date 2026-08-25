import pandas as pd
import numpy as np

class AdvancedSMCEngine:
    def __init__(self, min_rr=2.0, max_rr=8.0):
        self.min_rr = min_rr
        self.max_rr = max_rr
        self.active_setups = {}
        self.symbol_states = {}

    def check_fvg(self, df_15m, direction):
        if len(df_15m) < 3:
            return False
        c1_high = float(df_15m.iloc[-3]['high'])
        c3_low = float(df_15m.iloc[-1]['low'])
        c1_low = float(df_15m.iloc[-3]['low'])
        c3_high = float(df_15m.iloc[-1]['high'])

        if direction == "BUY" and c3_low > c1_high:
            return True
        if direction == "SELL" and c3_high < c1_low:
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

    def get_macro_external_liquidity_pools(self, df_1h):
        if len(df_1h) < 50:
            external_low = float(df_1h['low'].min())
            external_high = float(df_1h['high'].max())
        else:
            external_low = float(df_1h['low'].tail(50).min())
            external_high = float(df_1h['high'].tail(50).max())
        return external_low, external_high

    def get_opposing_liquidity_targets(self, df_1h, direction, entry, symbol):
        highs = df_1h['high'].tail(50).values
        lows = df_1h['low'].tail(50).values

        # Set appropriate fallback point increments based on asset type
        fallback_step = 5.0 if "XAU" in symbol else 0.0050

        if direction == "BUY":
            above_entry = [h for h in highs if h > entry]
            if not above_entry:
                tp1, tp2, tp3 = entry + fallback_step, entry + (fallback_step * 2), entry + (fallback_step * 3)
            else:
                sorted_highs = sorted(list(set(above_entry)))
                tp1 = sorted_highs[0]
                tp2 = sorted_highs[len(sorted_highs)//2] if len(sorted_highs) > 1 else tp1 + fallback_step
                tp3 = sorted_highs[-1]
        else:
            below_entry = [l for l in lows if l < entry]
            if not below_entry:
                tp1, tp2, tp3 = entry - fallback_step, entry - (fallback_step * 2), entry - (fallback_step * 3)
            else:
                sorted_lows = sorted(list(set(below_entry)), reverse=True)
                tp1 = sorted_lows[0]
                tp2 = sorted_lows[len(sorted_lows)//2] if len(sorted_lows) > 1 else tp1 - fallback_step
                tp3 = sorted_lows[-1]

        digits = 2 if "XAU" in symbol else 5
        return round(tp1, digits), round(tp2, digits), round(tp3, digits)

    def calculate_pnl_matrix(self, symbol, entry, sl, tp1, tp2):
        risk_distance = abs(entry - sl)
        
        if "XAU" in symbol:
            # Gold uses dollar/point scaling ($1.00 per point move)
            risk_pips_display = risk_distance
            tp1_pips_display = abs(tp1 - entry)
            tp2_pips_display = abs(tp2 - entry)
            dollar_multiplier = 100.0  # Standard 1 lot = 100 oz for gold
        else:
            # Forex uses standard pip scaling
            risk_pips_display = risk_distance * 10000 if risk_distance < 1.0 else risk_distance
            tp1_pips_display = abs(tp1 - entry) * 10000 if abs(tp1 - entry) < 1.0 else abs(tp1 - entry)
            tp2_pips_display = abs(tp2 - entry) * 10000 if abs(tp2 - entry) < 1.0 else abs(tp2 - entry)
            dollar_multiplier = 10.0

        lot_sizes = [0.01, 0.02, 0.03, 0.1, 0.2, 0.5, 1.0]
        matrix = []
        for lot in lot_sizes:
            dollar_per_unit = lot * dollar_multiplier
            matrix.append({
                "lot": lot,
                "loss": round(risk_pips_display * dollar_per_unit, 2),
                "tp1": round(tp1_pips_display * dollar_per_unit, 2),
                "tp2": round(tp2_pips_display * dollar_per_unit, 2)
            })
        return matrix, round(risk_pips_display, 2)

    def analyze(self, tf_data, symbol):
        df_4h = tf_data.get("4H")
        df_1h = tf_data.get("1H")
        df_15m = tf_data.get("15M")
        df_1m = tf_data.get("1M")

        if df_4h is None or df_1h is None or df_15m is None or df_1m is None:
            return {"status": "HOLD", "reason": "Missing multi-timeframe data feed"}

        if symbol not in self.symbol_states:
            self.symbol_states[symbol] = "SCANNING"

        # --- 1. 4H MACRO STRUCTURE BIAS ---
        swings_high = df_4h['high'].tail(10)
        swings_low = df_4h['low'].tail(10)
        is_higher_high = swings_high.iloc[-2] > swings_high.iloc[-5]
        is_higher_low = swings_low.iloc[-2] > swings_low.iloc[-5]
        bias = "BULLISH" if (is_higher_high and is_higher_low) else "BEARISH"

        # --- 2. EXTERNAL LIQUIDITY SWEEP CHECK ---
        historical_1h = df_1h.iloc[:-1]
        ext_low, ext_high = self.get_macro_external_liquidity_pools(historical_1h)
        
        current_1h_low = float(df_1h.iloc[-1]['low'])
        current_1h_high = float(df_1h.iloc[-1]['high'])
        current_price = float(df_1m.iloc[-1]['close'])

        sweep_direction = None
        swept_level = 0.0

        if current_1h_low <= ext_low:
            sweep_direction = "BUY"
            swept_level = ext_low
        elif current_1h_high >= ext_high:
            sweep_direction = "SELL"
            swept_level = ext_high

        if symbol in self.active_setups:
            setup = self.active_setups[symbol]
            if (setup['direction'] == "BUY" and current_price < setup['sl']) or \
               (setup['direction'] == "SELL" and current_price > setup['sl']):
                del self.active_setups[symbol]
                self.symbol_states[symbol] = "COOLDOWN"
                return {
                    "status": "INVALIDATED",
                    "symbol": symbol,
                    "reason": f"Price breached structural SL for active {setup['direction']} setup. Entering cooldown."
                }

        if self.symbol_states[symbol] == "COOLDOWN":
            if not sweep_direction:
                self.symbol_states[symbol] = "SCANNING"
            else:
                return {
                    "status": "HOLD",
                    "symbol": symbol,
                    "reason": "In state cooldown after previous setup invalidation/SL hit. Waiting for fresh cycle."
                }

        liq_fmt = f"{swept_level:.2f}" if "XAU" in symbol else f"{swept_level:.5f}"

        # --- 3. SETUP FORMING & FVG + BOS VALIDATION ---
        if sweep_direction and symbol not in self.active_setups and self.symbol_states[symbol] == "SCANNING":
            has_imbalance = self.check_fvg(df_15m, sweep_direction)
            structure_confirmed = self.check_bos_choch(df_15m, sweep_direction)

            if not (has_imbalance and structure_confirmed):
                active_level = ext_low if sweep_direction == "BUY" else ext_high
                active_liq_fmt = f"{active_level:.2f}" if "XAU" in symbol else f"{active_level:.5f}"
                high_fmt_val = f"{ext_high:.2f}" if "XAU" in symbol else f"{ext_high:.5f}"
                return {
                    "status": "LIQUIDITY_SWEPT",
                    "direction": sweep_direction,
                    "reason": f"Lows: {active_liq_fmt} | Highs: {high_fmt_val if sweep_direction=='BUY' else active_liq_fmt}"
                }

            choch_level = float(df_15m.iloc[-1]['close']) if float(df_15m.iloc[-1]['close']) > 0 else float(df_15m.iloc[-2]['close'])
            poi_level = float(df_15m['low'].tail(3).min()) if sweep_direction == "BUY" else float(df_15m['high'].tail(3).max())
            
            # --- CORRECTED BUFFER FOR GOLD VS FOREX ---
            buffer_val = 1.5 if "XAU" in symbol else 0.00030
            if sweep_direction == "BUY":
                sl = poi_level - buffer_val
            else:
                sl = poi_level + buffer_val
            
            self.active_setups[symbol] = {
                "bias": bias,
                "direction": sweep_direction,
                "choch_price": choch_level,
                "poi_price": poi_level,
                "sl": sl
            }
            self.symbol_states[symbol] = "WAITING_ENTRY"

            digits = 2 if "XAU" in symbol else 5
            return {
                "status": "CHOCH_CONFIRMED",
                "symbol": symbol,
                "direction": sweep_direction,
                "choch_price": choch_level,
                "poi_price": poi_level,
                "reason": f"External Liquidity Swept {liq_fmt} | 15M BOS Confirmed {sweep_direction} | Awaiting POI: {poi_level:.{digits}f}"
            }

        # --- 4. ACTIVE SETUP TRACKING ---
        if symbol in self.active_setups:
            setup = self.active_setups[symbol]
            direction = setup['direction']
            poi_level = setup['poi_price']
            choch_level = setup['choch_price']
            digits = 2 if "XAU" in symbol else 5
            p_fmt = f"{poi_level:.{digits}f}"
            
            entry = current_price
            sl = setup['sl']
            
            tp1, tp2, tp3 = self.get_opposing_liquidity_targets(df_1h, direction, entry, symbol)
            
            risk_dist = abs(entry - sl)
            reward_dist = abs(tp1 - entry)
            rr = reward_dist / risk_dist if risk_dist > 0.00001 else 0

            if self.min_rr <= rr <= self.max_rr:
                pnl_matrix, pips_risk = self.calculate_pnl_matrix(symbol, entry, sl, tp1, tp2)
                del self.active_setups[symbol]
                self.symbol_states[symbol] = "IN_TRADE"

                return {
                    "status": "TRIGGERED",
                    "decision": direction,
                    "reason": f"Execution confirmed inside Order Block (POI: {p_fmt}) targeting opposing liquidity.",
                    "trade_params": {
                        "entry": round(entry, digits),
                        "sl": round(sl, digits),
                        "tp1": tp1,
                        "tp2": tp2,
                        "tp3": tp3,
                        "rr": round(rr, 2),
                        "pips_risk": pips_risk,
                        "pnl_matrix": pnl_matrix
                    }
                }
            else:
                return {
                    "status": "CHOCH_CONFIRMED",
                    "symbol": symbol,
                    "direction": direction,
                    "choch_price": choch_level,
                    "poi_price": poi_level,
                    "reason": f"Liquidity Swept | Awaiting price retracement to Order Block ({p_fmt}) | Current RR: {rr:.2f}"
                }

        low_fmt = f"{ext_low:.2f}" if "XAU" in symbol else f"{ext_low:.5f}"
        high_fmt = f"{ext_high:.2f}" if "XAU" in symbol else f"{ext_high:.5f}"
        curr_fmt = f"{current_price:.2f}" if "XAU" in symbol else f"{current_price:.5f}"
        return {
            "status": "HOLD", 
            "reason": f"Scanning Bi-Directional External Sweeps [Lows: {low_fmt} | Highs: {high_fmt}] | Price: {curr_fmt}"
        }