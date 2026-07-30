"""
Change of Character (CHoCH) Engine

Detects the latest confirmed Change of Character (CHoCH)
by scanning all major swings after confirming the current
market structure.

Author: BMIE Project
"""

from models import CHoCHEvent


class CHoCHEngine:
    """
    Detects the latest confirmed Change of Character.
    """

    def __init__(self, context):
        self.context = context

    # ======================================================
    # Private Helpers
    # ======================================================

    def _empty_event(self) -> CHoCHEvent:
        return CHoCHEvent()

    # ======================================================
    # Bullish CHoCH
    # ======================================================

    def _detect_bullish_choch(self) -> CHoCHEvent:
        """
        Bullish CHoCH can only occur when the current
        market structure is Bearish.
        """

        if self.context.market_structure.trend != "Bearish":
            return self._empty_event()

        df = self.context.df
        latest_event = self._empty_event()

        for swing in self.context.swing_highs:

            if swing.time not in df.index:
                continue

            start_index = df.index.get_loc(swing.time)

            for i in range(start_index + 1, len(df)):

                close = float(df.iloc[i]["close"])

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

    def _detect_bearish_choch(self) -> CHoCHEvent:
        """
        Bearish CHoCH can only occur when the current
        market structure is Bullish.
        """

        if self.context.market_structure.trend != "Bullish":
            return self._empty_event()

        df = self.context.df
        latest_event = self._empty_event()

        for swing in self.context.swing_lows:

            if swing.time not in df.index:
                continue

            start_index = df.index.get_loc(swing.time)

            for i in range(start_index + 1, len(df)):

                close = float(df.iloc[i]["close"])

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

    def analyze(self) -> CHoCHEvent:
        """
        Returns the latest confirmed Change of Character.
        """

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