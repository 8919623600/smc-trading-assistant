"""
backtest/strategy_engine.py

BMIE Strategy Engine V5

Responsibilities
----------------
- Replay historical candles
- Build historical snapshots
- Prevent look-ahead bias
- Inject historical data into MarketEngine
- Extract BMIE signals

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
    # Create Trading Session
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
    # Extract BMIE Result
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


            "setup_quality":

                None,


            "entry_confirmation":

                None

        }





        # ------------------------------
        # Setup Quality
        # ------------------------------

        if engine.setup_quality:


            result["grade"] = (

                engine.setup_quality.grade

            )


            result["setup_quality"] = {


                "score":

                    engine.setup_quality.score,


                "grade":

                    engine.setup_quality.grade

            }





        # ------------------------------
        # Entry Confirmation
        # ------------------------------

        if engine.entry_confirmation:


            result["entry_confirmation"] = (

                engine.entry_confirmation

            )


            result["confidence"] = (

                engine.entry_confirmation.get(

                    "confidence",

                    0

                )

            )



            status = (

                engine.entry_confirmation.get(

                    "status",

                    ""

                )

            )



            if status == "ENTRY CONFIRMED":


                result["signal"] = (

                    "TRADE READY"

                )





        return result





    # ======================================================
    # Historical Replay
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



                # Create session

                session = self.create_session(

                    symbol,

                    exchange

                )





                # Build historical view

                market_snapshot = (

                    self.build_market_snapshot(

                        timeframe_data,

                        index

                    )

                )





                # Run BMIE engine

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





            except Exception as error:


                print(

                    "Backtest candle error:",

                    error

                )





        print(

            f"Signals generated: {len(signals)}"

        )



        return signals