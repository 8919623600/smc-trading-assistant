"""
smc/zone_engine.py

BMIE Demand Supply Zone Engine V5

Final tuning before MarketEngine integration.

Features:
- Base + displacement detection
- BOS confirmation
- ATR zone width filter
- Dynamic strength scoring
- Freshness scoring
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



    def calculate_atr(
        self,
        period=14
    ):

        ranges = []

        for i in range(1, len(self.df)):

            candle = self.df.iloc[i]

            prev = self.df.iloc[i-1]

            ranges.append(
                max(
                    candle.high - candle.low,
                    abs(candle.high - prev.close),
                    abs(candle.low - prev.close)
                )
            )

        if len(ranges) < period:
            return None

        return sum(
            ranges[-period:]
        ) / period



    def body_ratio(
        self,
        candle
    ):

        body = abs(
            candle.close -
            candle.open
        )

        total = (
            candle.high -
            candle.low
        )

        if total == 0:
            return 0

        return body / total



    def calculate_strength(
        self,
        displacement_strength,
        bos_strength,
        fresh
    ):

        score = 0


        # displacement 0-25

        score += min(
            int(displacement_strength * 25),
            25
        )


        # BOS 0-25

        score += min(
            int(bos_strength * 25),
            25
        )


        # freshness

        if fresh:
            score += 15


        # higher timeframe bonus

        if self.timeframe in [
            "1d",
            "4h"
        ]:

            score += 10


        # base quality

        score += 15


        return min(
            score,
            100
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

                merged.append(
                    current
                )

                current = zone


        merged.append(
            current
        )


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



        for i in range(
            3,
            len(self.df)-2
        ):

            base = self.df.iloc[i-1]

            move = self.df.iloc[i]


            displacement = (
                self.body_ratio(move)
            )


            if displacement < 0.6:

                continue



            previous = self.df.iloc[i-2]


            bullish_bos = (
                move.close >
                previous.high
            )


            bearish_bos = (
                move.close <
                previous.low
            )



            # Demand

            if (
                base.close < base.open
                and
                bullish_bos
            ):

                zone = Zone(

                    low=float(base.low),

                    high=float(base.high),

                    zone_type="Demand",

                    strength=self.calculate_strength(

                        displacement,

                        1.0,

                        True

                    )

                )


                if zone.width <= atr * 1.2:

                    demand.append(
                        zone
                    )



            # Supply

            if (
                base.close > base.open
                and
                bearish_bos
            ):

                zone = Zone(

                    low=float(base.low),

                    high=float(base.high),

                    zone_type="Supply",

                    strength=self.calculate_strength(

                        displacement,

                        1.0,

                        True

                    )

                )


                if zone.width <= atr * 1.2:

                    supply.append(
                        zone
                    )


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
