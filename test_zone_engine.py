"""
BMIE Zone Engine Test Runner

Purpose:
- Test Demand/Supply Zone detection independently
- Does NOT connect with MarketEngine
- Reads existing BMIE parquet cache

Run:
python test_zone_engine.py
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


def load_cache(timeframe):

    path = (
        f"backtest/cache/"
        f"{SYMBOL}_{timeframe}.parquet"
    )

    print(
        f"Loading {path}"
    )

    return pd.read_parquet(path)



def print_zones(
    timeframe,
    zones
):

    print()
    print("=" * 60)
    print(
        f"TIMEFRAME: {timeframe}"
    )
    print("=" * 60)


    demand = [
        z for z in zones
        if z.zone_type == "Demand"
    ]


    supply = [
        z for z in zones
        if z.zone_type == "Supply"
    ]


    print()
    print("DEMAND ZONES")
    print("-" * 30)


    if demand:

        for zone in demand:

            print(
                f"{zone.low} - {zone.high} | "
                f"Strength={zone.strength} | "
                f"Fresh={zone.fresh}"
            )

    else:

        print("No demand zones found")


    print()
    print("SUPPLY ZONES")
    print("-" * 30)


    if supply:

        for zone in supply:

            print(
                f"{zone.low} - {zone.high} | "
                f"Strength={zone.strength} | "
                f"Fresh={zone.fresh}"
            )

    else:

        print("No supply zones found")



def main():


    print(
        "BMIE DEMAND SUPPLY ZONE TEST"
    )


    for timeframe in TIMEFRAMES:

        df = load_cache(
            timeframe
        )


        engine = ZoneEngine(
            df,
            timeframe
        )


        zones = engine.analyze()


        print_zones(
            timeframe,
            zones
        )



if __name__ == "__main__":

    main()
