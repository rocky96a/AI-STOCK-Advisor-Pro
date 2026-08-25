import numpy as np
import pandas as pd

from backend.data.market_data import MarketData
from backend.indicators import trend, momentum, volatility, volume
from backend.ml.feature_engineering import build_features, build_labels


class UniversalDatasetBuilder:

    DEFAULT_SYMBOLS = [
        "RELIANCE.NS",
        "TCS.NS",
        "INFY.NS",
        "HDFCBANK.NS",
        "ICICIBANK.NS",
        "SBIN.NS",
        "ITC.NS",
        "LT.NS",
        "AXISBANK.NS",
        "KOTAKBANK.NS",
    ]

    def __init__(self):
        self.market = MarketData()

    def _prepare_indicators(self, df):
        df = df.copy()

        df = trend.calculate(df)
        df = momentum.calculate(df)
        df = volatility.calculate(df)
        df = volume.calculate(df)

        return df

    def build_stock(
        self,
        symbol,
        period="2y",
        interval="1d",
        horizon=5,
        atr_threshold=1.0,
    ):
        print(f"[UniversalDataset] Loading {symbol}")

        df = self.market.get_data(
            symbol=symbol,
            period=period,
            interval=interval,
        )

        if df is None or df.empty:
            print(
                f"[UniversalDataset] No data: {symbol}"
            )
            return None

        try:
            df = self._prepare_indicators(df)

            features = build_features(df)
            labels = build_labels(
                df,
                horizon=horizon,
                atr_threshold=atr_threshold,
            )

            data = features.copy()
            data["LABEL"] = labels
            data["SYMBOL"] = symbol

            data = data.replace(
                [np.inf, -np.inf],
                np.nan,
            )

            data = data.dropna(
                subset=list(features.columns)
                + ["LABEL"]
            )

            if data.empty:
                return None

            data["LABEL"] = (
                data["LABEL"]
                .astype(int)
            )

            return data.reset_index(
                drop=True
            )

        except Exception as exc:
            print(
                f"[UniversalDataset] "
                f"Failed {symbol}: {exc}"
            )
            return None

    def build(
        self,
        symbols=None,
        period="2y",
        interval="1d",
        horizon=5,
        atr_threshold=1.0,
    ):
        if symbols is None:
            symbols = self.DEFAULT_SYMBOLS

        datasets = []

        for symbol in symbols:

            data = self.build_stock(
                symbol=symbol,
                period=period,
                interval=interval,
                horizon=horizon,
                atr_threshold=atr_threshold,
            )

            if data is not None:
                datasets.append(data)

        if not datasets:
            return None

        combined = pd.concat(
            datasets,
            ignore_index=True,
        )

        combined = combined.sort_index()

        return combined
