from backtest.historical_loader import HistoricalLoader
from backtest.strategy_engine import StrategyEngine
from replay.replay_config import REPLAY_CASE



class ReplayEngine:


    def run(self):


        print("=" * 60)
        print("BMIE REPLAY ENGINE")
        print("=" * 60)


        loader = HistoricalLoader(
            exchange=REPLAY_CASE["exchange"]
        )


        data = loader.load_multi_timeframe(
            REPLAY_CASE["symbol"]
        )


        strategy = StrategyEngine()


        signals = strategy.run(

            REPLAY_CASE["symbol"],

            REPLAY_CASE["exchange"],

            data,

            start_index=REPLAY_CASE["candle_index"],

            max_candles=1

        )


        print()
        print("========== RESULT ==========")


        if not signals:

            print(
                "No TRADE READY signal generated"
            )

            return



        signal = signals[0]


        print(
            "Signal:",
            signal["signal"]
        )

        print(
            "Direction:",
            signal["direction"]
        )

        print(
            "Entry:",
            signal["entry"]
        )

        print(
            "Stop Loss:",
            signal["stop_loss"]
        )

        print(
            "Target:",
            signal["target"]
        )

        print(
            "RR:",
            signal["risk_reward"]
        )



if __name__ == "__main__":

    ReplayEngine().run()