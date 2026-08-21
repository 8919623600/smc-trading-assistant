import os
import pandas as pd
from twelvedata import TDClient

API_KEY = os.getenv("TWELVE_DATA_API_KEY_1")
SYMBOLS = ["EUR/USD", "XAU/USD"]

def analyze_structure():
    if not API_KEY:
        print("❌ ERROR: 'TWELVE_DATA_API_KEY_1' environment variable is missing.")
        return

    td = TDClient(apikey=API_KEY)

    print("==================================================")
    print("🔎 SMC MULTI-TIMEFRAME LEVEL DIAGNOSTIC")
    print("==================================================")

    for symbol in SYMBOLS:
        print(f"\n==================================================")
        print(f"📊 ASSET: {symbol}")
        print(f"==================================================")
        
        tf_data = {}
        intervals = {"4H": "4h", "1H": "1h", "15M": "15min", "5M": "5min", "1M": "1min"}
        
        success = True
        for tf_name, interval in intervals.items():
            try:
                # Corrected: using .as_pandas() method call
                ts = td.time_series(symbol=symbol, interval=interval, outputsize=100)
                df = ts.as_pandas()
                
                if df is not None and not df.empty:
                    df = df.reset_index()
                    if 'datetime' in df.columns:
                        df = df.rename(columns={'datetime': 'timestamp'})
                    tf_data[tf_name] = df
                else:
                    success = False
            except Exception as e:
                print(f"⚠️ Error fetching {tf_name} for {symbol}: {e}")
                success = False

        if not success or len(tf_data) < 5:
            print(f"❌ Could not fetch complete multi-timeframe data for {symbol}.")
            continue

        # 1. 4H Market Structure (Bias Check)
        df_4h = tf_data["4H"]
        last_4h_close = float(df_4h.iloc[-1]['close'])
        bias = "BULLISH 🟢" if last_4h_close > float(df_4h.iloc[-5]['close']) else "BEARISH 🔴"
        
        print(f"\n1️⃣ 4H MARKET STRUCTURE (BIAS):")
        print(f"   • Current 4H Close : {last_4h_close:.5f}")
        print(f"   • Market Bias      : {bias}")

        # 2. 1H Liquidity Points & Sweep Watch
        df_1h = tf_data["1H"]
        recent_1h_highs = float(df_1h['high'].tail(10).max())
        recent_1h_lows = float(df_1h['low'].tail(10).min())

        print(f"\n2️⃣ 1H LIQUIDITY POOL DETECTION:")
        print(f"   • Recent Equal Highs (EQH) : {recent_1h_highs:.5f}")
        print(f"   • Recent Equal Lows (EQL)  : {recent_1h_lows:.5f}")
        print(f"   • Liquidity Sweep Watch    : Looking for wicks sweeping beyond {recent_1h_highs:.5f} (for Sell) or {recent_1h_lows:.5f} (for Buy)")

        # 3. 15M POI & Structure
        df_15m = tf_data["15M"]
        recent_15m_high = float(df_15m['high'].tail(5).max())
        recent_15m_low = float(df_15m['low'].tail(5).min())
        
        print(f"\n3️⃣ 15M POI & STRUCTURE SETUP:")
        print(f"   • 15M Zone High/Resistance : {recent_15m_high:.5f}")
        print(f"   • 15M Zone Low/Support     : {recent_15m_low:.5f}")
        print(f"   • Target Setup             : Awaiting 15M CHoCH/BOS displacement inside this range.")

        # 4. 5M / 1M Execution Plan
        df_1m = tf_data["1M"]
        current_1m_price = float(df_1m.iloc[-1]['close'])
        
        print(f"\n4️⃣ 5M / 1M EXACT ENTRY PLAN:")
        print(f"   • Current 1M Price         : {current_1m_price:.5f}")
        print(f"   • Trigger Requirements     : 1M CHoCH + Displacement + FVG pullback.")
        print(f"   • Risk Management          : SL beyond 1M Invalidation Swing + ATR Buffer. Target Risk:Reward 2:1 to 8:1.")
        print("-" * 60)

if __name__ == "__main__":
    analyze_structure()