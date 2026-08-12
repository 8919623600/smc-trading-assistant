"""
BMIE Zone Selector Test V2

Purpose:
- Load cached zones
- Use real latest market price from parquet
- Test bullish and bearish selection
"""

import pandas as pd

from smc.zone_cache_manager import ZoneCacheManager
from smc.zone_selector import ZoneSelector


SYMBOL = "XAUUSD"
TIMEFRAME = "4h"


def print_zone(title, zone):

    print()
    print(title)

    if zone:

        print(
            "Zone:",
            f"{zone.low:.2f}",
            "-",
            f"{zone.high:.2f}"
        )

        print(
            "Type:",
            zone.zone_type
        )

        print(
            "Strength:",
            zone.strength
        )

        print(
            "Fresh:",
            zone.fresh
        )

    else:

        print("No valid zone selected")



def main():

    print("==============================")
    print("BMIE ZONE SELECTOR TEST V2")
    print("==============================")


    df = pd.read_parquet(
        f"backtest/cache/{SYMBOL}_{TIMEFRAME}.parquet"
    )


    current_price = float(
        df.iloc[-1].close
    )


    print(
        "Current Price:",
        current_price
    )


    cache = ZoneCacheManager()


    zones = cache.get_zones(
        SYMBOL,
        TIMEFRAME
    )


    if not zones:

        print(
            "No cache found. Run test_zone_cache.py first."
        )

        return


    selector = ZoneSelector(
        current_price=current_price
    )


    print_zone(
        "BULLISH TARGET",
        selector.select_target(
            zones,
            "Bullish"
        )
    )


    print_zone(
        "BULLISH ENTRY ZONE",
        selector.select_entry_zone(
            zones,
            "Bullish"
        )
    )


    print_zone(
        "BEARISH TARGET",
        selector.select_target(
            zones,
            "Bearish"
        )
    )


    print_zone(
        "BEARISH ENTRY ZONE",
        selector.select_entry_zone(
            zones,
            "Bearish"
        )
    )


if __name__ == "__main__":

    main()
