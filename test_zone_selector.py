"""
BMIE Zone Selector Test

Purpose:
- Load cached zones
- Test bullish target selection
- Test bearish target selection
"""

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

        print("No zone selected")


def main():

    print("==============================")
    print("BMIE ZONE SELECTOR TEST")
    print("==============================")


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


    current_price = 4265.01


    print(
        "Current Price:",
        current_price
    )


    selector = ZoneSelector(
        current_price=current_price
    )


    bullish_target = selector.select_target(
        zones,
        "Bullish"
    )


    bearish_target = selector.select_target(
        zones,
        "Bearish"
    )


    bullish_entry = selector.select_entry_zone(
        zones,
        "Bullish"
    )


    bearish_entry = selector.select_entry_zone(
        zones,
        "Bearish"
    )


    print_zone(
        "BULLISH TARGET",
        bullish_target
    )


    print_zone(
        "BULLISH ENTRY ZONE",
        bullish_entry
    )


    print_zone(
        "BEARISH TARGET",
        bearish_target
    )


    print_zone(
        "BEARISH ENTRY ZONE",
        bearish_entry
    )


if __name__ == "__main__":

    main()
