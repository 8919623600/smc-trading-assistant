"""
backtest/strategy_engine.py

BMIE Strategy Engine V7

Responsibilities
----------------
- Replay historical candles
- Prevent look-ahead bias
- Inject historical data into MarketEngine
- Extract BMIE signals
- Debug setup qualification

Author: BMIE Project
"""


import contextlib
import io


from core.session import TradingSession
from engine.market_engine import MarketEngine





class StrategyEngine:


    def __init__(
        self,
        balance=100000,
        verbose=False
    ):

        self.balance = balance
        self.verbose = verbose





    # ======================================================
    # Create Session
    # ======================================================

    def create_session(
        self,
        symbol,
        exchange
    ):

        return TradingSession(

            symbol=symbol,

            exchange=exchange,

            balance=self.balance

        )





    # ======================================================
    # Build Historical Snapshot
    # ======================================================

    def build_market_snapshot(
        self,
        timeframe_data,
        index
    ):

        snapshot = {}

        current_time = (

            timeframe_data["5m"]

            .iloc[index]

            .name

        )


        for timeframe, df in timeframe_data.items():

            snapshot[timeframe] = (

                df[
                    df.index <= current_time
                ]

                .copy()

            )


        return snapshot





    # ======================================================
    # Extract Signal
    # ======================================================

    def extract_signal(
        self,
        engine,
        candle_time
    ):


        result = {


            "symbol":
                engine.session.symbol,


            "exchange":
                engine.session.exchange,


            "time":
                str(candle_time),


            "signal":
                "NO TRADE",


            "confidence":
                0,


            "grade":
                None,


            "direction":
                None,


            "entry":
                None,


            "stop_loss":
                None,


            "target":
                None,


            "risk_reward":
                0

        }



        # ==================================================
        # Setup Quality Debug
        # ==================================================

        if engine.setup_quality:


            result["grade"] = (

                engine.setup_quality.grade

            )


            print(

                "QUALITY DEBUG:",

                engine.setup_quality.grade,

                engine.setup_quality.score

            )





        # ==================================================
        # Entry Confirmation Debug
        # ==================================================

        if engine.entry_confirmation:


            status = (

                engine.entry_confirmation.get(

                    "status",

                    ""

                )

            )


            confidence = (

                engine.entry_confirmation.get(

                    "confidence",

                    0

                )

            )


            result["confidence"] = confidence



            print(

                "ENTRY DEBUG:",

                status,

                confidence

            )



            if status == "ENTRY CONFIRMED":


                result["signal"] = (

                    "TRADE READY"

                )





        # ==================================================
        # Risk Extraction
        # ==================================================

        entry = engine.analysis.entry



        if entry and entry.risk_decision:


            risk = entry.risk_decision



            result["entry"] = (

                risk.entry_low

            )


            result["stop_loss"] = (

                risk.stop_loss

            )


            result["target"] = (

                risk.target

            )


            result["risk_reward"] = (

                risk.risk_reward

            )





        return result





    # ======================================================
    # Replay Historical Data
    # ======================================================

    def run(
        self,
        symbol,
        exchange,
        timeframe_data,
        start_index=100,
        max_candles=50
    ):


        signals = []

        skipped = 0


        candles = timeframe_data["5m"]



        end_index = min(

            len(candles),

            start_index + max_candles

        )



        total = end_index - start_index



        print(

            f"Backtesting candles: {total}"

        )





        for index in range(

            start_index,

            end_index

        ):


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



                market_snapshot = (

                    self.build_market_snapshot(

                        timeframe_data,

                        index

                    )

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





                if signal["signal"] != "NO TRADE":


                    signals.append(

                        signal

                    )

                else:

                    skipped += 1





            except Exception as error:


                print(

                    "Backtest candle error:",

                    error

                )





        print(

            "Signals generated:",

            len(signals)

        )


        print(

            "Skipped setups:",

            skipped

        )


        return signals