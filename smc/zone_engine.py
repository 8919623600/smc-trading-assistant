"""
smc/zone_engine.py

BMIE Demand Supply Zone Engine V1

Purpose:
- Detect institutional Demand and Supply zones
- Designed for BMIE multi timeframe architecture
- Initial standalone version
- No MarketEngine integration yet

Flow:
1D + 4H  -> Major zones
1H + 15M -> Refinement
5M        -> Entry confirmation only
"""

from dataclasses import dataclass


@dataclass
class DemandSupplyZone:

    zone_type: str

    high: float

    low: float

    timeframe: str

    strength: int = 0

    fresh: bool = True

    mitigated: bool = False

    created_index: int = None


class ZoneEngine:


    def __init__(
        self,
        df,
        timeframe
    ):

        self.df = df

        self.timeframe = timeframe

        self.zones = []


    # ======================================================
    # Displacement Detection
    # ======================================================

    def is_bullish_displacement(
        self,
        candle
    ):

        body = abs(
            candle["close"] -
            candle["open"]
        )

        candle_range = (
            candle["high"] -
            candle["low"]
        )


        if candle_range == 0:

            return False


        return (
            candle["close"] > candle["open"]
            and
            body / candle_range >= 0.6
        )


    def is_bearish_displacement(
        self,
        candle
    ):

        body = abs(
            candle["close"] -
            candle["open"]
        )

        candle_range = (
            candle["high"] -
            candle["low"]
        )


        if candle_range == 0:

            return False


        return (
            candle["open"] > candle["close"]
            and
            body / candle_range >= 0.6
        )


    # ======================================================
    # Demand Zone Detection
    # ======================================================

    def detect_demand_zones(self):

        zones = []


        for i in range(
            2,
            len(self.df) - 1
        ):

            previous = self.df.iloc[i-1]

            current = self.df.iloc[i]


            if (
                previous["close"] < previous["open"]
                and
                self.is_bullish_displacement(current)
            ):

                zone = DemandSupplyZone(

                    zone_type="Demand",

                    high=float(previous["high"]),

                    low=float(previous["low"]),

                    timeframe=self.timeframe,

                    strength=60,

                    created_index=i

                )

                zones.append(zone)


        return zones


    # ======================================================
    # Supply Zone Detection
    # ======================================================

    def detect_supply_zones(self):

        zones = []


        for i in range(
            2,
            len(self.df) - 1
        ):

            previous = self.df.iloc[i-1]

            current = self.df.iloc[i]


            if (
                previous["close"] > previous["open"]
                and
                self.is_bearish_displacement(current)
            ):

                zone = DemandSupplyZone(

                    zone_type="Supply",

                    high=float(previous["high"]),

                    low=float(previous["low"]),

                    timeframe=self.timeframe,

                    strength=60,

                    created_index=i

                )

                zones.append(zone)


        return zones


    # ======================================================
    # Analyze Zones
    # ======================================================

    def analyze(self):

        demand_zones = (
            self.detect_demand_zones()
        )


        supply_zones = (
            self.detect_supply_zones()
        )


        self.zones = (
            demand_zones +
            supply_zones
        )


        return self.zones
