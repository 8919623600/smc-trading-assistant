"""
smc/zone_selector.py

BMIE Zone Selector V1

Purpose:
- Select relevant cached demand/supply zones
- Filter zones by current price
- Rank zones by strength and distance
- Provide logical targets for MarketEngine
"""

from dataclasses import dataclass


class ZoneSelector:


    def __init__(
        self,
        current_price,
        max_distance=None
    ):

        self.current_price = current_price

        self.max_distance = max_distance



    def distance_from_price(
        self,
        zone
    ):

        if zone.low <= self.current_price <= zone.high:

            return 0


        if self.current_price < zone.low:

            return zone.low - self.current_price


        return self.current_price - zone.high



    def relevance_score(
        self,
        zone
    ):

        distance = self.distance_from_price(
            zone
        )


        score = zone.strength


        if distance == 0:

            score += 30

        elif self.max_distance:

            if distance <= self.max_distance:

                score += 20

            else:

                score -= 20


        return score



    def select_target(
        self,
        zones,
        direction
    ):

        if not zones:

            return None


        candidates = []


        for zone in zones:


            # Bullish trade targets supply above price

            if direction == "Bullish":

                if zone.zone_type != "Supply":

                    continue


                if zone.low <= self.current_price:

                    continue



            # Bearish trade targets demand below price

            if direction == "Bearish":

                if zone.zone_type != "Demand":

                    continue


                if zone.high >= self.current_price:

                    continue



            score = self.relevance_score(
                zone
            )


            candidates.append(
                (
                    score,
                    zone
                )
            )


        if not candidates:

            return None


        candidates.sort(
            key=lambda x: x[0],
            reverse=True
        )


        return candidates[0][1]



    def select_entry_zone(
        self,
        zones,
        direction
    ):

        if not zones:

            return None


        candidates = []


        for zone in zones:


            if direction == "Bullish":

                if zone.zone_type != "Demand":

                    continue


            if direction == "Bearish":

                if zone.zone_type != "Supply":

                    continue


            score = self.relevance_score(
                zone
            )


            candidates.append(
                (
                    score,
                    zone
                )
            )


        if not candidates:

            return None


        candidates.sort(
            key=lambda x: x[0],
            reverse=True
        )


        return candidates[0][1]
