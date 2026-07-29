from tvDatafeed import TvDatafeed, Interval

tv = TvDatafeed()

intervals = {
    "1m": Interval.in_1_minute,
    "5m": Interval.in_5_minute,
    "15m": Interval.in_15_minute,
    "1h": Interval.in_1_hour,
    "4h": Interval.in_4_hour,
    "1d": Interval.in_daily
}

def get_data(tf, bars=500):
    return tv.get_hist(
        symbol="XAUUSD",
        exchange="OANDA",
        interval=intervals[tf],
        n_bars=bars
    )
