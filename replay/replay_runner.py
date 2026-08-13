"""
Replay Runner V1

Purpose:
Replay exact historical chart points and compare
SMC engine output with manual TradingView analysis.
"""


from backtest.historical_loader import HistoricalLoader
from backtest.strategy_engine import StrategyEngine
from engine.market_engine import MarketEngine
from core.session import TradingSession


import json
import os



class ReplayRunner:


    def __init__(self):

        self.symbol = "XAUUSD"
        self.exchange = "OANDA"



    def load_case(self, path):

        with open(path, "r") as file:

            return json.load(file)



    def find_candle_index(
        self,
        df,
        target_time
    ):

        matches = df[
            df["time"] == target_time
        ]


        if matches.empty:

            raise Exception(
                f"Candle not found: {target_time}"
            )


        return matches.index[0]



    def run_case(
        self,
        case_file
    ):


        case = self.load_case(
            case_file
        )


        print("=" * 60)
        print("REPLAY TEST")
        print("=" * 60)



        loader = HistoricalLoader(
            exchange=self.exchange
        )


        data = loader.load_multi_timeframe(
            self.symbol
        )


        target_time = case["entry_time"]



        index = self.find_candle_index(
            data["5m"],
            target_time
        )


        print(
            "Replay candle index:",
            index
        )


        print(
            "Replay time:",
            target_time
        )



        snapshot = {}

        for tf in [
            "1d",
            "4h",
            "1h",
            "15m",
            "5m"
        ]:

            snapshot[tf] = (
                data[tf]
                [
                    data[tf]["time"]
                    <= target_time
                ]
                .copy()
            )



        session = TradingSession(
            symbol=self.symbol,
            exchange=self.exchange,
            balance=100000
        )

        print(
            "SNAPSHOT 5M END:",
            snapshot["5m"].iloc[-1]["time"]
        )

        print(
            "SNAPSHOT 15M END:",
            snapshot["15m"].iloc[-1]["time"]
        )

        print(
            "SNAPSHOT 1H END:",
            snapshot["1h"].iloc[-1]["time"]
        )


        engine = MarketEngine(
            session,
            market_data=snapshot,
            backtest=True
        )


        engine.run()



        print("\nENGINE RESULT")
        print("----------------")


        print(
            "Direction:",
            getattr(
                engine.analysis.entry.trade_decision,
                "direction",
                None
            )
        )


        print(
            "Signal:",
            getattr(
                engine.analysis.entry.trade_decision,
                "signal",
                None
            )
        )


        print(
            "Order Block:",
            engine.selected_order_block
        )


        print(
            "Target:",
            engine.target_liquidity
        )



        print("\nEXPECTED")
        print("----------------")


        print(
            case["expected"]
        )





if __name__ == "__main__":


    runner = ReplayRunner()


    runner.run_case(
        "replay/cases/xauusd_20260804_buy_ob.json"
    )