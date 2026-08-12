"""
smc/zone_engine.py

BMIE Zone Engine V2

Purpose:
- Detect cleaner SMC demand and supply zones
- Avoid hundreds of weak zones
- Require displacement
- Merge overlapping zones
- Rank zones by strength

V2 Logic:
1. Find base candles
2. Confirm displacement move
3. Create demand/supply zone
4. Calculate strength
5. Merge overlapping zones
6. Return strongest zones
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
    def level(self):
        return (self.low + self.high) / 2


class ZoneEngine:

    def __init__(
        self,
        df,
        max_zones=3,
        min_strength=70
    ):
        self.df = df
        self.max_zones = max_zones
        self.min_strength = min_strength


    def calculate_strength(
        self,
        displacement=False,
        fresh=True,
        bos=False
    ):

        score = 0

        if displacement:
            score += 30

        if fresh:
            score += 20

        if bos:
            score += 30

        score += 20

        return min(score, 100)


    def detect_zones(self):

        demand = []
        supply = []

        candles = self.df.reset_index(drop=True)

        for i in range(2, len(candles)-2):

            current = candles.iloc[i]

            previous = candles.iloc[i-1]

            next_candle = candles.iloc[i+1]


            body = abs(
                current.close -
                current.open
            )


            candle_range = (
                current.high -
                current.low
            )


            if candle_range == 0:
                continue


            strength_move = (
                body / candle_range
            )


            displacement = strength_move > 0.6


            # Demand:
            # bearish candle followed by strong bullish move

            if (
                previous.close < previous.open
                and current.close > current.open
                and displacement
            ):

                zone = Zone(
                    low=previous.low,
                    high=previous.high,
                    zone_type="Demand",
                    strength=self.calculate_strength(
                        displacement=True,
                        fresh=True,
                        bos=True
                    )
                )

                if zone.strength >= self.min_strength:
                    demand.append(zone)


            # Supply:
            # bullish candle followed by strong bearish move

            if (
                previous.close > previous.open
                and current.close < current.open
                and displacement
            ):

                zone = Zone(
                    low=previous.low,
                    high=previous.high,
                    zone_type="Supply",
                    strength=self.calculate_strength(
                        displacement=True,
                        fresh=True,
                        bos=True
                    )
                )

                if zone.strength >= self.min_strength:
                    supply.append(zone)


        return (
            self.merge_zones(demand)[:self.max_zones],
            self.merge_zones(supply)[:self.max_zones]
        )


    def merge_zones(
        self,
        zones
    ):

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


    def analyze(self):

        demand, supply = self.detect_zones()

        return {
            "demand": demand,
            "supply": supply
        }
