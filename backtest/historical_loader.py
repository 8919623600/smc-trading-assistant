"""
backtest/historical_loader.py

BMIE Historical Loader V2

Features:
- Loads TradingView historical data
- Persistent parquet cache
- Avoids repeated downloads
- Faster backtesting
"""

import os
import pandas as pd

from data.tv_datafeed import TVDataFeed


class HistoricalLoader:


    def __init__(
        self,
        exchange="OANDA"
    ):

        self.exchange = exchange

        self.cache_dir = (
            "backtest/cache"
        )

        os.makedirs(
            self.cache_dir,
            exist_ok=True
        )

        self.tv = TVDataFeed()



    # ==================================================
    # Cache File
    # ==================================================

    def cache_file(
        self,
        symbol,
        timeframe
    ):

        return os.path.join(

            self.cache_dir,

            f"{symbol}_{timeframe}.parquet"

        )



    # ==================================================
    # Load One Timeframe
    # ==================================================

    def load_timeframe(
        self,
        symbol,
        timeframe
    ):


        file = self.cache_file(
            symbol,
            timeframe
        )


        # ------------------------------
        # Load Cache
        # ------------------------------

        if os.path.exists(file):

            print(
                f"Loading cache {timeframe}"
            )

            df = pd.read_parquet(
                file
            )

            return df



        # ------------------------------
        # Download
        # ------------------------------

        print(
            f"Downloading {symbol} {timeframe} data..."
        )


        df = self.tv.get_hist(

            symbol=symbol,

            exchange=self.exchange,

            interval=timeframe,

            n_bars=5000

        )


        if df is None:

            raise Exception(
                f"No data received {timeframe}"
            )


        df.reset_index(
            inplace=True
        )


        df.rename(

            columns={

                "datetime":
                "time"

            },

            inplace=True

        )


        df["symbol"] = (

            f"{self.exchange}:{symbol}"

        )


        # Save cache

        df.to_parquet(
            file,
            index=False
        )


        print(
            f"Saved cache {file}"
        )


        return df



    # ==================================================
    # Multi Timeframe Loader
    # ==================================================

    def load_multi_timeframe(
        self,
        symbol
    ):


        timeframes = {

            "1d":
            "1D",

            "4h":
            "4H",

            "1h":
            "60",

            "15m":
            "15",

            "5m":
            "5"

        }


        data = {}


        for name, interval in timeframes.items():


            print(
                f"Loading {symbol} {name} data..."
            )


            data[name] = self.load_timeframe(

                symbol,

                interval

            )


        return data