import requests
import pandas as pd
from config import TWELVE_DATA_API_KEYS

class TwelveDataFetcher:
    def __init__(self):
        self.keys = TWELVE_DATA_API_KEYS
        self.key_index = 0

    def _get_active_key(self):
        if not self.keys:
            return None
        return self.keys[self.key_index % len(self.keys)]

    def _rotate_key(self):
        if len(self.keys) > 1:
            self.key_index = (self.key_index + 1) % len(self.keys)
            print(f"🔄 Rotating to backup Twelve Data API key (Index {self.key_index})")

    def fetch_candles(self, symbol, interval="1min", outputsize=100):
        api_key = self._get_active_key()
        if not api_key:
            print("❌ No Twelve Data API keys found in environment variables!")
            return None

        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize={outputsize}&apikey={api_key}&format=JSON"

        try:
            response = requests.get(url, timeout=10)
            data = response.json()

            if "code" in data and data["code"] != 200:
                print(f"⚠️ Twelve Data API Error ({symbol} - {interval}): {data.get('message')}")
                if "rate limit" in str(data.get('message')).lower():
                    self._rotate_key()
                return None

            if "values" not in data:
                return None

            df = pd.DataFrame(data["values"])
            df.rename(columns={"datetime": "time"}, inplace=True)
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = df[col].astype(float)
            
            df['time'] = pd.to_datetime(df['time'])
            df.sort_values('time', inplace=True)
            df.reset_index(drop=True, inplace=True)
            return df

        except Exception as e:
            print(f"❌ Exception fetching data for {symbol} ({interval}): {e}")
            return None

    def get_market_data(self, symbol):
        df_1m = self.fetch_candles(symbol, interval="1min", outputsize=100)
        df_15m = self.fetch_candles(symbol, interval="15min", outputsize=100)
        df_4h = self.fetch_candles(symbol, interval="4h", outputsize=100)

        return {
            "1M": df_1m,
            "15M": df_15m,
            "4H": df_4h
        }