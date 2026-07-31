"""
backtest/strategy_engine.py

BMIE Strategy Engine V2

Responsibilities
----------------
- Replay historical candles
- Connect with existing BMIE analyzer
- Generate backtest signals

Author: BMIE Project
"""


import importlib





class StrategyEngine:


    def __init__(self):

        self.analyzer = self.load_analyzer()





    # ======================================================
    # Load BMIE Analyzer Dynamically
    # ======================================================

    def load_analyzer(self):

        try:

            module = importlib.import_module(
                "analyzer"
            )


            if hasattr(
                module,
                "analyze_market"
            ):

                return module.analyze_market



            if hasattr(
                module,
                "Analyzer"
            ):

                analyzer = module.Analyzer()

                return analyzer.run



        except Exception as error:

            print(
                "Analyzer loading failed:",
                error
            )


        return None





    # ======================================================
    # Analyze Historical Candle
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

            "time": str(
                timeframe_data["5m"]
                .iloc[index]["time"]
            ),

            "signal": "NO TRADE",

            "confidence": 0,

            "grade": None,

            "direction": None,

            "entry": None,

            "stop_loss": None,

            "target": None

        }



        if self.analyzer is None:

            return result





        try:


            analysis = self.analyzer(

                symbol,

                exchange,

                timeframe_data

            )



            if analysis:


                result["analysis"] = analysis



                if isinstance(
                    analysis,
                    dict
                ):


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


                    result["direction"] = (

                        analysis.get(
                            "direction"
                        )

                    )


                    result["entry"] = (

                        analysis.get(
                            "entry"
                        )

                    )


                    result["stop_loss"] = (

                        analysis.get(
                            "stop_loss"
                        )

                    )


                    result["target"] = (

                        analysis.get(
                            "target"
                        )

                    )



        except Exception as error:


            result["error"] = str(error)



        return result





    # ======================================================
    # Run Historical Replay
    # ======================================================

    def run(
        self,
        symbol,
        exchange,
        timeframe_data,
        start_index=100
    ):


        signals = []



        candles = len(
            timeframe_data["5m"]
        )



        for index in range(

            start_index,

            candles

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