"""
backtest/historical_loader.py

BMIE Historical Data Loader V2

Features:

- Load historical market candles
- Support multi timeframe backtesting
- Persistent parquet cache
- Avoid repeated TradingView downloads

Author: BMIE Project
"""


import os
import pandas as pd

from tvDatafeed import TvDatafeed, Interval



class HistoricalLoader:


    def __init__(
        self,
        exchange="OANDA"
    ):

        self.exchange = exchange

        self.tv = TvDatafeed()


        # Persistent cache location

        self.cache_dir = (
            "backtest/cache"
        )


        os.makedirs(
            self.cache_dir,
            exist_ok=True
        )



    # ======================================================
    # Timeframe Mapping
    # ======================================================

    def get_interval(
        self,
        timeframe
    ):


        mapping = {


            "1m":
                Interval.in_1_minute,


            "5m":
                Interval.in_5_minute,


            "15m":
                Interval.in_15_minute,


            "30m":
                Interval.in_30_minute,


            "1h":
                Interval.in_1_hour,


            "4h":
                Interval.in_4_hour,


            "1d":
                Interval.in_daily

        }



        if timeframe not in mapping:

            raise ValueError(

                f"Unsupported timeframe: {timeframe}"

            )


        return mapping[timeframe]



    # ======================================================
    # Cache File Path
    # ======================================================

    def cache_file(
        self,
        symbol,
        timeframe
    ):


        return os.path.join(

            self.cache_dir,

            f"{symbol}_{timeframe}.parquet"

        )



    # ======================================================
    # Load Historical Data
    # ======================================================

    def load_data(
        self,
        symbol,
        timeframe,
        bars=5000
    ):


        cache = self.cache_file(

            symbol,

            timeframe

        )


        # ==================================================
        # Load From Cache
        # ==================================================

        if os.path.exists(cache):


            print(

                f"Loading cache {symbol} {timeframe}"

            )


            return pd.read_parquet(

                cache

            )



        # ==================================================
        # Download From TradingView
        # ==================================================

        interval = self.get_interval(

            timeframe

        )


        print(

            f"Loading {symbol} {timeframe} data..."

        )



        df = self.tv.get_hist(

            symbol=symbol,

            exchange=self.exchange,

            interval=interval,

            n_bars=bars

        )



        if df is None:


            raise RuntimeError(

                f"No historical data found for {symbol}"

            )



        df = df.reset_index()



        df.rename(

            columns={

                "datetime":

                    "time"

            },

            inplace=True

        )



        # ==================================================
        # Save Cache
        # ==================================================

        df.to_parquet(

            cache,

            index=False

        )


        print(

            f"Saved cache {cache}"

        )



        return df



    # ======================================================
    # Load Multi Timeframe Data
    # ======================================================

    def load_multi_timeframe(
        self,
        symbol
    ):


        timeframes = [

            "1d",

            "4h",

            "1h",

            "15m",

            "5m"

        ]


        data = {}



        for timeframe in timeframes:


            data[timeframe] = self.load_data(

                symbol,

                timeframe

            )



        return data