"""
backtest/run_backtest.py

BMIE Backtest Runner V1.1

Fix:
- Uses StrategyEngine signal directly
- Removes dependency on signal["analysis"]
- Keeps trade simulation flow intact
"""

from backtest.historical_loader import HistoricalLoader
from backtest.strategy_engine import StrategyEngine
from backtest.trade_simulator import TradeSimulator
from backtest.backtest_report import BacktestReport


class BMIEBacktest:


    def __init__(self):

        self.symbol = "XAUUSD"
        self.exchange = "OANDA"



    # ======================================================
    # Convert Signal To Trade
    # ======================================================

    def map_signal_to_trade(self, signal):

        if signal.get("signal") != "TRADE READY":
            return None


        confirmation = signal.get(
            "confirmation_status"
        )


        if confirmation not in [
            "ENTRY CONFIRMED"
        ]:
            return None


        risk = signal.get(
            "risk_decision"
        )


        if risk:

            if not getattr(
                risk,
                "valid",
                False
            ):
                return None


        entry = signal.get("entry")
        stop_loss = signal.get("stop_loss")
        target = signal.get("target")


        if (
            entry is None
            or stop_loss is None
            or target is None
        ):
            return None


        trade = {

            "symbol":
                signal.get(
                    "symbol",
                    self.symbol
                ),

            "time":
                signal.get(
                    "time"
                ),

            "direction":
                signal.get(
                    "direction",
                    "BUY"
                ),

            "entry":
                entry,

            "stop_loss":
                stop_loss,

            "target":
                target,

            "grade":
                signal.get(
                    "grade"
                )

        }


        return trade



    # ======================================================
    # Run Backtest
    # ======================================================

    def run(self):


        print("=" * 60)
        print("BMIE BACKTEST ENGINE V1")
        print("=" * 60)



        loader = HistoricalLoader(
            exchange=self.exchange
        )


        data = loader.load_multi_timeframe(
            self.symbol
        )


        print(
            "Historical data loaded"
        )



        strategy = StrategyEngine()



        signals = strategy.run(
            self.symbol,
            self.exchange,
            data,
            start_index=4000,
            max_candles=5
        )


        print(
            f"Signals generated: {len(signals)}"
        )



        simulator = TradeSimulator()


        trades = []



        for signal in signals:


            trade = self.map_signal_to_trade(
                signal
            )


            if not trade:
                continue



            entry_time = signal.get("time")

            print(
                "SIGNAL TIME:",
                entry_time
            )


            future_candles = data["5m"][
                data["5m"]["time"] > entry_time
            ]

            print(
                "SIMULATING TRADE:",
                trade
            )


            result = simulator.simulate(
                trade,
                future_candles
            )


            result["rr"] = simulator.calculate_rr(
                result
            )


            trades.append(
                result
            )



        print(
            f"Trades simulated: {len(trades)}"
        )



        report = BacktestReport(
            trades
        )


        report.print_report()



if __name__ == "__main__":

    engine = BMIEBacktest()

    engine.run()
