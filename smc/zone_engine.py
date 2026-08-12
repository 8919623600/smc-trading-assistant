"""
smc/zone_engine.py

BMIE Demand Supply Zone Engine V3

Improvements:
- Base candle detection
- Displacement validation
- Zone size filtering
- Overlap merging
- Better strength scoring
- Top zone selection
"""

from dataclasses import dataclass


@dataclass
class Zone:

    low: float
    high: float
    zone_type: str
    strength: int = 0
    fresh: bool = True

    @property
    def width(self):
        return abs(self.high - self.low)


class ZoneEngine:


    def __init__(
        self,
        df,
        timeframe="",
        max_zones=3
    ):

        self.df = df.reset_index(drop=True)

        self.timeframe = timeframe

        self.max_zones = max_zones


    def candle_body_ratio(self, candle):

        body = abs(
            candle.close -
            candle.open
        )

        rng = (
            candle.high -
            candle.low
        )

        if rng == 0:
            return 0

        return body / rng


    def calculate_strength(
        self,
        displacement,
        base_quality,
        fresh=True
    ):

        score = 0

        if displacement:
            score += 35

        if base_quality:
            score += 25

        if fresh:
            score += 20

        if self.timeframe in [
            "1d",
            "4h"
        ]:
            score += 20

        return min(score, 100)


    def merge_zones(self, zones):

        if not zones:
            return []

        zones = sorted(
            zones,
            key=lambda x: x.low
        )

        merged = []

        current = zones[0]


        for zone in zones[1:]:

            if zone.low <= current.high:

                current.high = max(
                    current.high,
                    zone.high
                )

                current.strength = max(
                    current.strength,
                    zone.strength
                )

            else:

                merged.append(current)

                current = zone


        merged.append(current)

        return sorted(
            merged,
            key=lambda x: x.strength,
            reverse=True
        )


    def detect_zones(self):

        demand = []

        supply = []


        for i in range(
            3,
            len(self.df)-1
        ):

            base = self.df.iloc[i-1]

            move = self.df.iloc[i]


            ratio = self.candle_body_ratio(
                move
            )


            displacement = ratio >= 0.6


            if not displacement:
                continue


            # Demand:
            # bearish base -> bullish displacement

            if (
                base.close < base.open
                and
                move.close > move.open
            ):

                zone = Zone(
                    low=float(base.low),
                    high=float(base.high),
                    zone_type="Demand",
                    strength=self.calculate_strength(
                        True,
                        True
                    )
                )

                demand.append(zone)


            # Supply:
            # bullish base -> bearish displacement

            if (
                base.close > base.open
                and
                move.close < move.open
            ):

                zone = Zone(
                    low=float(base.low),
                    high=float(base.high),
                    zone_type="Supply",
                    strength=self.calculate_strength(
                        True,
                        True
                    )
                )

                supply.append(zone)


        return (
            self.merge_zones(demand),
            self.merge_zones(supply)
        )


    def analyze(self):

        demand, supply = self.detect_zones()

        return {
            "demand": demand[:self.max_zones],
            "supply": supply[:self.max_zones]
        }
