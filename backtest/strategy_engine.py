"""
backtest/strategy_engine.py

BMIE Strategy Engine V9

Fix:
- Updated RiskDecision fields
- Uses risk.entry instead of risk.entry_low
"""

import contextlib
import io

from core.session import TradingSession
from engine.market_engine import MarketEngine


class StrategyEngine:

    def __init__(self, balance=100000, verbose=False):
        self.balance = balance
        self.verbose = verbose

    def create_session(self, symbol, exchange):
        return TradingSession(
            symbol=symbol,
            exchange=exchange,
            balance=self.balance
        )

    def build_market_snapshot(self, timeframe_data, index):

        snapshot = {}

        current_time = (
            timeframe_data["5m"]
            .iloc[index]
            .name
        )

        for timeframe, df in timeframe_data.items():

            snapshot[timeframe] = (
                df[df.index <= current_time]
                .copy()
            )

        return snapshot


    def extract_signal(self, engine, candle_time):

        result = {
            "symbol": engine.session.symbol,
            "exchange": engine.session.exchange,
            "time": str(candle_time),
            "signal": "NO TRADE",
            "confidence": 0,
            "grade": None,
            "entry": None,
            "stop_loss": None,
            "target": None,
            "risk_reward": 0,
            "setup_quality": None,
            "entry_confirmation": None
        }


        grade = None
        confidence = 0


        if engine.setup_quality:

            grade = engine.setup_quality.grade

            result["grade"] = grade

            result["setup_quality"] = {
                "score": engine.setup_quality.score,
                "grade": grade
            }

            print(
                "QUALITY:",
                grade,
                engine.setup_quality.score
            )


        risk_available = False
        risk = None


        if engine.analysis.entry and engine.analysis.entry.risk_decision:

            risk = engine.analysis.entry.risk_decision
            risk_available = True


        if engine.entry_confirmation:

            result["entry_confirmation"] = engine.entry_confirmation

            confidence = engine.entry_confirmation.get(
                "confidence",
                0
            )

            result["confidence"] = confidence

            print(
                "ENTRY:",
                engine.entry_confirmation.get("status"),
                confidence
            )


        if risk_available and risk:

            print(
                "RISK DEBUG:",
                risk.entry,
                risk.stop_loss,
                risk.target,
                risk.risk_reward
            )

            result["entry"] = risk.entry
            result["stop_loss"] = risk.stop_loss
            result["target"] = risk.target
            result["risk_reward"] = risk.risk_reward

        else:

            print(
                "RISK DEBUG: NO RISK PLAN"
            )


        if (
            grade in ["A", "B"]
            and confidence >= 65
            and risk_available
        ):

            result["signal"] = "TRADE READY"


        return result


    def run(
        self,
        symbol,
        exchange,
        timeframe_data,
        start_index=100,
        max_candles=50
    ):

        signals = []

        candles = timeframe_data["5m"]

        end_index = min(
            len(candles),
            start_index + max_candles
        )

        print(
            f"Backtesting candles: {end_index-start_index}"
        )


        for index in range(start_index, end_index):

            print(
                f"Processing candle {index}"
            )

            try:

                candle_time = (
                    candles.iloc[index]
                    .name
                )

                session = self.create_session(
                    symbol,
                    exchange
                )

                market_snapshot = self.build_market_snapshot(
                    timeframe_data,
                    index
                )

                engine = MarketEngine(
                    session,
                    market_data=market_snapshot
                )


                if self.verbose:
                    engine.run()

                else:

                    with contextlib.redirect_stdout(
                        io.StringIO()
                    ):
                        engine.run()


                signal = self.extract_signal(
                    engine,
                    candle_time
                )


                if signal["signal"] == "TRADE READY":

                    signals.append(signal)


            except Exception as error:

                import traceback

                print(
                    "Backtest candle error:",
                    error
                )

                traceback.print_exc()


        print(
            "Signals generated:",
            len(signals)
        )

        return signals
