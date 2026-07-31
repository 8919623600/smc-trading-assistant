"""
backtest/strategy_engine.py

BMIE Strategy Engine V1

Responsibilities
----------------
- Replay historical candles
- Run BMIE analysis on historical data
- Generate backtest signals
- Prepare trades for simulator

Author: BMIE Project
"""


from datetime import datetime





class StrategyEngine:


    def __init__(
        self,
        analyzer
    ):

        self.analyzer = analyzer





    # ======================================================
    # Analyze Historical Point
    # ======================================================

    def analyze_point(
        self,
        symbol,
        exchange,
        timeframe_data,
        index
    ):


        result = {


            "symbol": symbol,

            "exchange": exchange,

            "time": None,

            "signal": "NO TRADE",

            "confidence": 0,

            "grade": None,

            "analysis": None


        }





        try:


            candle = timeframe_data["5m"].iloc[index]


            result["time"] = str(

                candle["time"]

            )



            analysis = self.analyzer.run(


                symbol,

                exchange,

                timeframe_data,

                index


            )



            result["analysis"] = analysis





            if analysis:


                result["signal"] = (

                    analysis.get(

                        "signal",

                        "NO TRADE"

                    )

                )


                result["confidence"] = (

                    analysis.get(

                        "confidence",

                        0

                    )

                )


                result["grade"] = (

                    analysis.get(

                        "grade"

                    )

                )



        except Exception as error:


            result["error"] = str(error)



        return result





    # ======================================================
    # Run Backtest Loop
    # ======================================================

    def run(
        self,
        symbol,
        exchange,
        timeframe_data,
        start_index=100
    ):


        signals = []



        total_candles = len(

            timeframe_data["5m"]

        )



        for index in range(

            start_index,

            total_candles

        ):


            result = self.analyze_point(

                symbol,

                exchange,

                timeframe_data,

                index

            )



            if result["signal"] != "NO TRADE":


                signals.append(

                    result

                )



        return signals