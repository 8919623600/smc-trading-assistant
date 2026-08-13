"""
backtest/strategy_engine.py

BMIE Strategy Engine V9.2

Fix:
- Updated RiskDecision fields
- Uses risk.entry
- Uses candle time column instead of dataframe index
- Supports RiskManager V5.2
- Generates TRADE READY signals
- Prevents duplicate trades from same Order Block
"""

import contextlib
import io

from core.session import TradingSession
from engine.market_engine import MarketEngine
from backtest.analysis_cache import AnalysisCache


class StrategyEngine:

    def __init__(
        self,
        balance=100000,
        verbose=True,
        analysis_cache=None
    ):

        self.balance = balance
        self.verbose = verbose
        self.htf_cache = {}
        self.analysis_cache = analysis_cache

        # Track already used institutional order blocks
        self.used_order_blocks = set()


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
            .iloc[index]["time"]
        )

        # IMPORTANT: In backtesting, every timeframe must contain
        # only candles available at the current 5M candle time.
        # This prevents future-data leakage.
        for timeframe in [
            "1d",
            "4h",
            "1h",
            "15m",
            "5m"
        ]:

            snapshot[timeframe] = (
                timeframe_data[timeframe]
                [
                    timeframe_data[timeframe]["time"]
                    <= current_time
                ]
            ).copy()

        return snapshot


    def extract_signal(self, engine, candle_time):

        result = {
            "symbol": engine.session.symbol,
            "exchange": engine.session.exchange,
            "time": candle_time,
            "signal": "NO TRADE",
            "confidence": 0,
            "grade": None,
            "entry": None,
            "stop_loss": None,
            "target": None,
            "risk_reward": 0,
            "direction": None,
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


        risk = None
        risk_available = False


        if (
            engine.analysis.entry
            and
            engine.analysis.entry.risk_decision
        ):

            risk = engine.analysis.entry.risk_decision

            if (
                getattr(risk, "entry", None) is not None
                and
                getattr(risk, "stop_loss", None) is not None
                and
                getattr(risk, "target", None) is not None
            ):

                risk_available = True



        print(
            "FULL RISK OBJECT DEBUG:",
            "entry=",
            getattr(risk, "entry", None),
            "sl=",
            getattr(risk, "stop_loss", None),
            "target=",
            getattr(risk, "target", None),
            "rr=",
            getattr(risk, "risk_reward", None),
            "valid=",
            getattr(risk, "valid", None),
            "reason=",
            getattr(risk, "reason", None)
        )


        if risk_available:

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

            result["direction"] = getattr(
                risk,
                "direction",
                None
            )

        else:

            print(
                "RISK DEBUG: NO RISK PLAN",
                getattr(risk, "reason", "unknown")
            )


        confirmation_status = ""

        if engine.entry_confirmation:

            confirmation_status = engine.entry_confirmation.get(
                "status",
                ""
            )

        risk_valid = bool(
            risk_available
            and
            getattr(risk, "valid", False)
        )


        if (
            grade in ["A", "B"]
            and
            confidence >= 65
            and
            confirmation_status == "ENTRY CONFIRMED"
            and
            risk_valid
        ):

            ob = engine.selected_order_block

            if ob:

                ob_id = getattr(
                    ob,
                    "created_at",
                    None
                )

                if ob_id in self.used_order_blocks:

                    print(
                        "DUPLICATE OB SKIPPED:",
                        ob_id
                    )

                    return result


                self.used_order_blocks.add(ob_id)


            result["signal"] = "TRADE READY"


        return result


    def run(
        self,
        symbol,
        exchange,
        timeframe_data,
        start_index=100,
        max_candles=10
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


        for index in range(
            start_index,
            end_index
        ):

            print(
                f"Processing candle {index}"
            )

            try:

                candle_time = candles.iloc[index]["time"]

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
                    market_data=market_snapshot,
                    backtest=True,
                    analysis_cache=self.analysis_cache
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
