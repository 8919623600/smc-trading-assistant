"""
backtest/historical_loader.py

BMIE Historical Data Loader V1

Responsibilities
----------------
- Load historical market candles
- Support multi timeframe backtesting
- Provide data for BMIE analyzer

Author: BMIE Project
"""


from tvDatafeed import TvDatafeed, Interval
import pandas as pd





class HistoricalLoader:


    def __init__(
        self,
        exchange="OANDA"
    ):

        self.exchange = exchange


        self.tv = TvDatafeed()





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
    # Load Historical Data
    # ======================================================

    def load_data(
        self,
        symbol,
        timeframe,
        bars=5000
    ):


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



        return df





    # ======================================================
    # Load Multi Timeframe Data
    # ======================================================

    def load_multi_timeframe(
        self,
        symbol
    ):


        data = {}



        timeframes = [

            "1d",

            "4h",

            "1h",

            "15m",

            "5m"

        ]



        for tf in timeframes:


            data[tf] = self.load_data(

                symbol,

                tf

            )



        return data





    # ======================================================
    # Validate Data
    # ======================================================

    def validate(
        self,
        df
    ):


        required = [

            "open",

            "high",

            "low",

            "close",

            "volume"

        ]



        for column in required:


            if column not in df.columns:


                raise ValueError(

                    f"Missing column: {column}"

                )



        return True





if __name__ == "__main__":


    loader = HistoricalLoader(

        exchange="OANDA"

    )


    data = loader.load_multi_timeframe(

        "XAUUSD"

    )


    for tf, df in data.items():


        print(

            tf,

            len(df),

            "candles"

        )