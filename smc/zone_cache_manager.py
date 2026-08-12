"""
smc/zone_cache_manager.py

BMIE Zone Cache Manager V1

Purpose:
- Store calculated demand/supply zones
- Avoid recalculating zone engine every run
- Support timeframe based cache
- Validate cache freshness
"""

import os
import pickle
from datetime import datetime, timedelta


class ZoneCacheManager:


    def __init__(
        self,
        cache_dir="backtest/cache/zones"
    ):

        self.cache_dir = cache_dir

        os.makedirs(
            self.cache_dir,
            exist_ok=True
        )


    def get_cache_file(
        self,
        symbol,
        timeframe
    ):

        return os.path.join(
            self.cache_dir,
            f"{symbol}_{timeframe}_zones.pkl"
        )


    def save_zones(
        self,
        symbol,
        timeframe,
        zones,
        last_candle=None
    ):

        data = {

            "symbol": symbol,

            "timeframe": timeframe,

            "created": datetime.now(),

            "last_candle": last_candle,

            "zones": zones

        }


        file = self.get_cache_file(
            symbol,
            timeframe
        )


        with open(
            file,
            "wb"
        ) as f:

            pickle.dump(
                data,
                f
            )


        return file



    def load_zones(
        self,
        symbol,
        timeframe
    ):

        file = self.get_cache_file(
            symbol,
            timeframe
        )


        if not os.path.exists(file):

            return None


        with open(
            file,
            "rb"
        ) as f:

            return pickle.load(f)



    def is_cache_valid(
        self,
        symbol,
        timeframe
    ):

        data = self.load_zones(
            symbol,
            timeframe
        )


        if not data:

            return False


        created = data.get(
            "created"
        )


        if not created:

            return False


        expiry = self.get_expiry(
            timeframe
        )


        return (
            datetime.now() - created
            <
            expiry
        )



    def get_expiry(
        self,
        timeframe
    ):

        expiry_map = {

            "1d": timedelta(days=1),

            "4h": timedelta(hours=4),

            "1h": timedelta(hours=1),

            "15m": timedelta(minutes=15),

            "5m": timedelta(minutes=5)

        }


        return expiry_map.get(
            timeframe,
            timedelta(hours=1)
        )



    def get_zones(
        self,
        symbol,
        timeframe
    ):

        if self.is_cache_valid(
            symbol,
            timeframe
        ):

            data = self.load_zones(
                symbol,
                timeframe
            )

            return data.get(
                "zones"
            )


        return None



    def clear_cache(
        self,
        symbol=None
    ):

        files = os.listdir(
            self.cache_dir
        )


        for file in files:

            if symbol:

                if not file.startswith(symbol):
                    continue


            os.remove(
                os.path.join(
                    self.cache_dir,
                    file
                )
            )
