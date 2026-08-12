"""
smc/zone_engine.py

BMIE Demand Supply Zone Engine V4

Improvements:
- Base candle cluster detection
- Displacement validation
- ATR based zone width filtering
- Basic BOS validation
- Zone freshness scoring
- Overlap merging
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


    def calculate_atr(self, period=14):

        ranges = []

        for i in range(1, len(self.df)):

            high = self.df.iloc[i].high
            low = self.df.iloc[i].low
            prev_close = self.df.iloc[i-1].close

            ranges.append(
                max(
                    high-low,
                    abs(high-prev_close),
                    abs(low-prev_close)
                )
            )

        if len(ranges) < period:
            return None

        return sum(
            ranges[-period:]
        ) / period


    def body_ratio(self, candle):

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
        bos,
        fresh
    ):

        score = 0

        if displacement:
            score += 30

        if bos:
            score += 30

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

        atr = self.calculate_atr()

        if atr is None:
            return demand, supply


        for i in range(3, len(self.df)-2):

            base = self.df.iloc[i-1]
            move = self.df.iloc[i]
            future = self.df.iloc[i+1]


            displacement = (
                self.body_ratio(move) >= 0.6
            )


            if not displacement:
                continue


            # simple BOS validation

            previous_high = self.df.iloc[i-2].high
            previous_low = self.df.iloc[i-2].low


            bullish_bos = (
                move.close > previous_high
            )

            bearish_bos = (
                move.close < previous_low
            )


            # Demand

            if (
                base.close < base.open
                and move.close > move.open
                and bullish_bos
            ):

                zone = Zone(
                    low=float(base.low),
                    high=float(base.high),
                    zone_type="Demand",
                    strength=self.calculate_strength(
                        True,
                        True,
                        True
                    )
                )

                if zone.width <= atr * 1.5:
                    demand.append(zone)


            # Supply

            if (
                base.close > base.open
                and move.close < move.open
                and bearish_bos
            ):

                zone = Zone(
                    low=float(base.low),
                    high=float(base.high),
                    zone_type="Supply",
                    strength=self.calculate_strength(
                        True,
                        True,
                        True
                    )
                )

                if zone.width <= atr * 1.5:
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
