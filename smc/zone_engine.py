"""
smc/zone_engine.py

BMIE Demand Supply Zone Engine V7

Improvements:

- Current price relevance scoring
- Freshness validation
- Broken zone invalidation
- Better strength distribution
- Liquidity/location aware ranking
- ATR zone filtering
- BOS + displacement confirmation

Before MarketEngine integration.
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

        return abs(
            self.high - self.low
        )


    @property
    def level(self):

        return (
            self.low + self.high
        ) / 2



class ZoneEngine:


    def __init__(
        self,
        df,
        timeframe="",
        max_zones=3
    ):

        self.df = df.reset_index(
            drop=True
        )

        self.timeframe = timeframe

        self.max_zones = max_zones

        self.current_price = float(
            self.df.iloc[-1].close
        )



    def calculate_atr(
        self,
        period=14
    ):

        ranges = []


        for i in range(1, len(self.df)):

            candle = self.df.iloc[i]

            previous = self.df.iloc[i-1]


            ranges.append(

                max(

                    candle.high - candle.low,

                    abs(
                        candle.high -
                        previous.close
                    ),

                    abs(
                        candle.low -
                        previous.close
                    )

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



    def location_score(
        self,
        zone
    ):

        distance = abs(
            self.current_price -
            zone.level
        )


        atr = self.calculate_atr()


        if not atr:

            return 0


        if distance <= atr:

            return 10


        if distance <= atr * 3:

            return 5


        return 0



    def calculate_strength(
        self,
        displacement,
        bos,
        fresh,
        zone
    ):

        score = 0


        score += min(
            int(displacement * 30),
            30
        )


        if bos:

            score += 25


        if fresh:

            score += 20


        if self.timeframe in [
            "1d",
            "4h"
        ]:

            score += 10


        score += self.location_score(
            zone
        )


        return min(
            score,
            100
        )

        def check_freshness(
            self,
            zone,
            start
        ):

            future = self.df.iloc[
                start + 1:
            ]


            if future.empty:

                return True



            # Zone touched / mitigated

            touched = (

                (future["low"] <= zone.high)

                &

                (future["high"] >= zone.low)

            )


            if touched.any():

                return False



            # Supply invalidated by bullish breakout

            if zone.zone_type == "Supply":

                broken = (
                    future["close"]
                    >
                    zone.high
                )


                if broken.any():

                    return False



            # Demand invalidated by bearish breakdown

            if zone.zone_type == "Demand":

                broken = (
                    future["close"]
                    <
                    zone.low
                )


                if broken.any():

                    return False



            return True





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





        def detect_zones(
            self
        ):

            demand = []

            supply = []


            atr = self.calculate_atr()


            if atr is None:

                return demand, supply



            for i in range(
                3,
                len(self.df)-2
            ):


                if i % 500 == 0:

                    print(
                        "Processing zone candle:",
                        i
                    )



                base = self.df.iloc[i-1]

                move = self.df.iloc[i]

                previous = self.df.iloc[i-2]



                displacement = self.body_ratio(
                    move
                )



                if displacement < 0.6:

                    continue



                bullish_bos = (
                    move.close >
                    previous.high
                )


                bearish_bos = (
                    move.close <
                    previous.low
                )



                # ==========================================
                # Demand Zone
                # ==========================================

                if (
                    base.close < base.open

                    and

                    bullish_bos
                ):


                    zone = Zone(

                        low=float(base.low),

                        high=float(base.high),

                        zone_type="Demand"

                    )



                    zone.fresh = self.check_freshness(
                        zone,
                        i
                    )



                    zone.strength = self.calculate_strength(

                        displacement,

                        True,

                        zone.fresh,

                        zone

                    )



                    if (

                        zone.width <= atr * 1.2

                        and

                        zone.fresh

                    ):

                        demand.append(
                            zone
                        )





                # ==========================================
                # Supply Zone
                # ==========================================

                if (
                    base.close > base.open

                    and

                    bearish_bos
                ):


                    zone = Zone(

                        low=float(base.low),

                        high=float(base.high),

                        zone_type="Supply"

                    )



                    zone.fresh = self.check_freshness(
                        zone,
                        i
                    )



                    zone.strength = self.calculate_strength(

                        displacement,

                        True,

                        zone.fresh,

                        zone

                    )



                    if (

                        zone.width <= atr * 1.2

                        and

                        zone.fresh

                    ):

                        supply.append(
                            zone
                        )



            return (

                self.merge_zones(
                    demand
                ),

                self.merge_zones(
                    supply
                )

            )





        def analyze(
            self
        ):


            demand, supply = self.detect_zones()



            return {

                "demand":
                    demand[:self.max_zones],


                "supply":
                    supply[:self.max_zones]

            }