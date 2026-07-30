import pandas as pd


def get_trend(df):
    """
    Simple trend detection using last 20 candles.
    """

    sma20 = df["close"].rolling(20).mean()

    current = df["close"].iloc[-1]
    avg = sma20.iloc[-1]

    if current > avg:
        return "Bullish"

    elif current < avg:
        return "Bearish"

    else:
        return "Sideways"
