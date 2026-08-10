"""
BMIE Analysis Cache

Stores expensive SMC calculations
"""

import os
import pickle


class AnalysisCache:

    def __init__(self, symbol):

        self.symbol = symbol

        self.cache_dir = (
            "backtest/cache/analysis"
        )

        os.makedirs(
            self.cache_dir,
            exist_ok=True
        )


    def file(self, name):

        return os.path.join(
            self.cache_dir,
            f"{self.symbol}_{name}.pkl"
        )


    def save(self, name, data):

        with open(
            self.file(name),
            "wb"
        ) as f:

            pickle.dump(
                data,
                f
            )


    def load(self, name):

        file = self.file(name)

        if not os.path.exists(file):
            return None

        with open(
            file,
            "rb"
        ) as f:

            return pickle.load(f)