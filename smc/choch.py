"""
Change of Character (CHoCH) Engine

Detects structural reversal points.

CHoCH represents a possible change in market direction,
not a confirmed trend continuation.

Author: BMIE Project
"""

from models import CHoCHEvent


class CHoCHEngine:
    """
    Detects Change of Character from market structure.
    """

    def __init__(self, context):
        self.context = context


    # ======================================================
    # Helpers
    # ======================================================

    def _empty_event(self):
        return CHoCHEvent()


    # ======================================================
    # Bullish CHoCH
    # ======================================================

    def _detect_bullish_choch(self):

        structure = self.context.market_structure

        # Bullish CHoCH only happens from bearish structure
        if structure.trend != "Bearish":
            return self._empty_event()


        df = self.context.df

        latest_event = self._empty_event()


        for swing in self.context.swing_highs:

            if swing.time not in df.index:
                continue


            start_index = df.index.get_loc(
                swing.time
            )


            for i in range(start_index + 1, len(df)):

                close = float(
                    df.iloc[i]["close"]
                )


                # Break above previous lower high
                if close > swing.price:

                    latest_event = CHoCHEvent(
                        direction="Bullish",
                        level=swing.price,
                        time=df.index[i],
                        confirmed=True,
                    )

                    break


        return latest_event


    # ======================================================
    # Bearish CHoCH
    # ======================================================

    def _detect_bearish_choch(self):

        structure = self.context.market_structure


        # Bearish CHoCH only happens from bullish structure
        if structure.trend != "Bullish":
            return self._empty_event()


        df = self.context.df

        latest_event = self._empty_event()


        for swing in self.context.swing_lows:

            if swing.time not in df.index:
                continue


            start_index = df.index.get_loc(
                swing.time
            )


            for i in range(start_index + 1, len(df)):

                close = float(
                    df.iloc[i]["close"]
                )


                # Break below previous higher low
                if close < swing.price:

                    latest_event = CHoCHEvent(
                        direction="Bearish",
                        level=swing.price,
                        time=df.index[i],
                        confirmed=True,
                    )

                    break


        return latest_event


    # ======================================================
    # Public API
    # ======================================================

    def analyze(self):

        bullish = self._detect_bullish_choch()

        bearish = self._detect_bearish_choch()


        if bullish.confirmed and bearish.confirmed:

            if bullish.time >= bearish.time:
                return bullish

            return bearish


        if bullish.confirmed:
            return bullish


        if bearish.confirmed:
            return bearish


        return self._empty_event()