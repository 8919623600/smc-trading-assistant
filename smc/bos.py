"""
Break of Structure (BOS) Engine

Detects the latest confirmed Break of Structure (BOS)
by scanning all major swings and all subsequent candles.
"""

from models import BOSEvent


class BOSEngine:
    """
    Detects the latest confirmed Break of Structure.
    """

    def __init__(self, context):
        self.context = context

    # ======================================================
    # Private Helpers
    # ======================================================

    def _empty_event(self) -> BOSEvent:
        return BOSEvent()

    def _detect_bullish_bos(self) -> BOSEvent:
        """
        Find the latest bullish BOS.
        """

        latest_event = self._empty_event()

        df = self.context.df

        for swing in self.context.swing_highs:

            # Ignore swings that are not present in dataframe index
            if swing.time not in df.index:
                continue

            start_idx = df.index.get_loc(swing.time)

            for i in range(start_idx + 1, len(df)):

                close = float(df.iloc[i]["close"])

                if close > swing.price:

                    latest_event = BOSEvent(
                        direction="Bullish",
                        level=swing.price,
                        time=df.index[i],
                        confirmed=True,
                    )

                    swing.broken = True

                    break

        return latest_event

    def _detect_bearish_bos(self) -> BOSEvent:
        """
        Find the latest bearish BOS.
        """

        latest_event = self._empty_event()

        df = self.context.df

        for swing in self.context.swing_lows:

            if swing.time not in df.index:
                continue

            start_idx = df.index.get_loc(swing.time)

            for i in range(start_idx + 1, len(df)):

                close = float(df.iloc[i]["close"])

                if close < swing.price:

                    latest_event = BOSEvent(
                        direction="Bearish",
                        level=swing.price,
                        time=df.index[i],
                        confirmed=True,
                    )

                    swing.broken = True

                    break

        return latest_event

    # ======================================================
    # Public API
    # ======================================================

    def analyze(self) -> BOSEvent:
        """
        Returns the latest confirmed BOS.
        """

        bullish = self._detect_bullish_bos()
        bearish = self._detect_bearish_bos()

        if bullish.confirmed and bearish.confirmed:

            if bullish.time >= bearish.time:
                return bullish

            return bearish

        if bullish.confirmed:
            return bullish

        if bearish.confirmed:
            return bearish

        return self._empty_event()