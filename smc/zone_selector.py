"""
smc/zone_selector.py

BMIE Zone Selector V2

Purpose:

- Select relevant cached demand/supply zones
- Filter invalidated zones
- Filter zones by current price
- Rank zones by strength and distance
- Provide logical targets and entries for MarketEngine
"""



class ZoneSelector:


    def __init__(
        self,
        current_price,
        max_distance=None
    ):

        self.current_price = current_price

        self.max_distance = max_distance



    # ======================================================
    # Zone Invalidation
    # ======================================================

    def is_invalidated(
        self,
        zone
    ):

        # Supply broken by bullish move
        if zone.zone_type == "Supply":

            if self.current_price > zone.high:

                return True



        # Demand broken by bearish move
        if zone.zone_type == "Demand":

            if self.current_price < zone.low:

                return True



        return False



    # ======================================================
    # Distance From Current Price
    # ======================================================

    def distance_from_price(
        self,
        zone
    ):

        if zone.low <= self.current_price <= zone.high:

            return 0



        if self.current_price < zone.low:

            return zone.low - self.current_price



        return self.current_price - zone.high



    # ======================================================
    # Zone Relevance Score
    # ======================================================

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



    # ======================================================
    # Select Target Zone
    # ======================================================

    def select_target(
        self,
        zones,
        direction
    ):

        if not zones:

            return None



        candidates = []



        for zone in zones:



            # Ignore already broken zones

            if self.is_invalidated(zone):

                continue



            # ==========================
            # Bullish Target
            # Supply above price
            # ==========================

            if direction == "Bullish":


                if zone.zone_type != "Supply":

                    continue



                if zone.low <= self.current_price:

                    continue



            # ==========================
            # Bearish Target
            # Demand below price
            # ==========================

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



    # ======================================================
    # Select Entry Zone
    # ======================================================

    def select_entry_zone(
        self,
        zones,
        direction
    ):

        if not zones:

            return None



        candidates = []



        for zone in zones:



            # Ignore invalidated zones

            if self.is_invalidated(zone):

                continue



            # Bullish entry = Demand

            if direction == "Bullish":


                if zone.zone_type != "Demand":

                    continue



            # Bearish entry = Supply

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