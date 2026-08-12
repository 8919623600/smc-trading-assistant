"""
BMIE Zone Cache Test

Purpose:
- Verify ZoneEngine calculation
- Verify ZoneCacheManager save/load
- Ensure second run uses cache
"""

import pandas as pd

from smc.zone_engine import ZoneEngine
from smc.zone_cache_manager import ZoneCacheManager


SYMBOL = "XAUUSD"
TIMEFRAME = "4h"

CACHE = ZoneCacheManager()


def load_data():

    path = (
        f"backtest/cache/"
        f"{SYMBOL}_{TIMEFRAME}.parquet"
    )

    return pd.read_parquet(path)



def print_zones(zones):

    if not zones:

        print("No zones found")
        return


    for zone in zones:

        print(
            f"{zone.zone_type}: "
            f"{zone.low:.2f} - "
            f"{zone.high:.2f} "
            f"| Strength={zone.strength} "
            f"| Fresh={zone.fresh}"
        )



def first_run():

    print()
    print("==============================")
    print("FIRST RUN")
    print("==============================")


    df = load_data()


    engine = ZoneEngine(
        df,
        timeframe=TIMEFRAME
    )


    result = engine.analyze()


    zones = (
        result["demand"] +
        result["supply"]
    )


    CACHE.save_zones(
        SYMBOL,
        TIMEFRAME,
        zones,
        last_candle=len(df)
    )


    print(
        "Zones calculated and saved"
    )


    print_zones(
        zones
    )



def second_run():

    print()
    print("==============================")
    print("SECOND RUN")
    print("==============================")


    zones = CACHE.get_zones(
        SYMBOL,
        TIMEFRAME
    )


    if zones:

        print(
            "CACHE HIT ✅"
        )

        print_zones(
            zones
        )


    else:

        print(
            "CACHE MISS ❌"
        )



if __name__ == "__main__":

    first_run()

    second_run()
