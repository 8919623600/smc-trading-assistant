import pandas as pd
import numpy as np
import os

os.makedirs('data', exist_ok=True)

def create_dummy_csv(filename, periods=500, start_price=1.0800):
    np.random.seed(42)
    dates = pd.date_range(start="2026-01-01", periods=periods, freq="1H")
    
    change = np.random.normal(0, 0.0010, periods)
    close = start_price + np.cumsum(change)
    high = close + np.random.uniform(0.0002, 0.0015, periods)
    low = close - np.random.uniform(0.0002, 0.0015, periods)
    open_p = close - change / 2
    volume = np.random.randint(100, 5000, periods)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': open_p,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    })
    df.to_csv(filename, index=False)
    print(f"Generated mock file: {filename}")

create_dummy_csv("data/eurusd_4h.csv", periods=200)
create_dummy_csv("data/eurusd_1h.csv", periods=500)
create_dummy_csv("data/eurusd_15m.csv", periods=1000)
create_dummy_csv("data/eurusd_1m.csv", periods=2000)
pri:::nt("All mock files created successfully!")
