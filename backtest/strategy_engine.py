"""
backtest/strategy_engine.py

BMIE Strategy Engine V3

Responsibilities
----------------
- Replay historical candles
- Create BMIE trading sessions
- Run existing MarketEngine
- Extract BMIE decisions
- Generate backtest signals

Author: BMIE Project
"""


from core.session import TradingSession
from engine.market_engine import MarketEngine





class StrategyEngine:


    def __init__(
        self,
        balance=100000
    ):

        self.balance = balance





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



        # -------------------------------
        # Setup Quality
        # -------------------------------

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





        # -------------------------------
        # Entry Confirmation
        # -------------------------------

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





        # -------------------------------
        # Determine Signal
        # -------------------------------

        if engine.entry_confirmation:


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
        max_candles=None
    ):


        signals = []



        candles = timeframe_data["5m"]



        total = len(candles)



        if max_candles:


            total = min(

                total,

                start_index + max_candles

            )





        for index in range(

            start_index,

            total

        ):



            current_time = (

                candles.iloc[index]["time"]

            )



            try:


                session = self.create_session(

                    symbol,

                    exchange

                )



                engine = MarketEngine(

                    session

                )



                engine.run()



                signal = self.extract_signal(

                    engine,

                    current_time

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





        return signals