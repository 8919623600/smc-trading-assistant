"""
BMIE Zone Engine Compact Test Runner

Purpose:
- Display only top Demand/Supply zones
- Easy TradingView comparison
"""

import pandas as pd

from smc.zone_engine import ZoneEngine


SYMBOL = "XAUUSD"

TIMEFRAMES = [
    "1d",
    "4h",
    "1h",
    "15m",
]


MAX_DISPLAY = 3



def load_cache(timeframe):

    path = (
        f"backtest/cache/"
        f"{SYMBOL}_{timeframe}.parquet"
    )

    return pd.read_parquet(path)



def print_compact(
    timeframe,
    result
):

    print()
    print("=" * 35)
    print(timeframe.upper())
    print("=" * 35)


    demand = result.get(
        "demand",
        []
    )[:MAX_DISPLAY]


    supply = result.get(
        "supply",
        []
    )[:MAX_DISPLAY]


    print()
    print(
        f"DEMAND ({len(demand)})"
    )


    for i, zone in enumerate(
        demand,
        1
    ):

        print(
            f"{i}) {zone.low:.2f} - {zone.high:.2f} "
            f"({zone.strength})"
        )


    print()

    print(
        f"SUPPLY ({len(supply)})"
    )


    for i, zone in enumerate(
        supply,
        1
    ):

        print(
            f"{i}) {zone.low:.2f} - {zone.high:.2f} "
            f"({zone.strength})"
        )



def main():

    print(
        "BMIE DEMAND SUPPLY ZONE SUMMARY"
    )


    for timeframe in TIMEFRAMES:


        df = load_cache(
            timeframe
        )


        engine = ZoneEngine(
            df
        )


        result = engine.analyze()


        print_compact(
            timeframe,
            result
        )



if __name__ == "__main__":

    main()
