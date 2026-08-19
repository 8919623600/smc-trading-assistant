import pandas as pd

def check_csv_files():
    timeframes = ["4H", "1H", "15M", "1M"]
    file_paths = {
        "4H": "data/eurusd_4h.csv",
        "1H": "data/eurusd_1h.csv",
        "15M": "data/eurusd_15m.csv",
        "1M": "data/eurusd_1m.csv"
    }
    
    for tf in timeframes:
        try:
            df = pd.read_csv(file_paths[tf])
            print(f"✅ [{tf}] Successfully loaded! Total rows: {len(df)}")
            print(f"   Columns found: {list(df.columns)}")
        except FileNotFoundError:
            print(f"❌ [{tf}] File not found at path: {file_paths[tf]}. Check your folder path.")
        except Exception as e:
            print(f"⚠️ [{tf}] Error reading file: {e}")

if __name__ == "__main__":
    check_csv_files()