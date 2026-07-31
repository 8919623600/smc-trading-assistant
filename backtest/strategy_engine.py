"""
backtest/strategy_engine.py

BMIE Strategy Engine V4

Responsibilities
----------------
- Replay historical candles
- Run MarketEngine silently
- Extract BMIE signals
- Avoid console pollution
- Prepare data for simulator

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
                None

        }



        if engine.setup_quality:


            result["grade"] = (

                engine.setup_quality.grade

            )



        if engine.entry_confirmation:


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


                result["signal"] = "TRADE READY"





        return result





    # ======================================================
    # Run Replay
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



            try:


                candle_time = (

                    candles.iloc[index]["time"]

                )



                session = self.create_session(

                    symbol,

                    exchange

                )



                engine = MarketEngine(

                    session,
                    market_data=timeframe_data

                )





                # Silence MarketEngine output

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





                if self.verbose:


                    print(

                        f"Processed candle {index}"

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