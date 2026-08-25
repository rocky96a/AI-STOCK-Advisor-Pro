from pathlib import Path

import pandas as pd

from backend.features.indicators import Indicators
from backend.features.label_builder import LabelBuilder
from backend.ml.dataset import DatasetBuilder


class GlobalDatasetBuilder:

    DEFAULT_SYMBOLS = [
        "RELIANCE.NS",
        "TCS.NS",
        "INFY.NS",
        "HDFCBANK.NS",
        "ICICIBANK.NS",
        "SBIN.NS",
        "ITC.NS",
        "BHARTIARTL.NS",
        "LT.NS",
        "AXISBANK.NS",
        "KOTAKBANK.NS",
        "BAJFINANCE.NS",
        "MARUTI.NS",
        "SUNPHARMA.NS",
        "TITAN.NS",
        "WIPRO.NS",
        "ONGC.NS",
        "NTPC.NS",
        "ULTRACEMCO.NS",
        "HINDUNILVR.NS",

        # Global assets
        "TSLA",
        "BTC-USD",
    ]

    CACHE_DIR = Path("backend/data/cache/market")

    def __init__(self):
        self.builder = DatasetBuilder()

    def _load_cached_data(self, symbol):

        filename = (
            symbol.replace("/", "_")
            .replace(".", "_")
            + "_1d.csv"
        )

        path = self.CACHE_DIR / filename

        if not path.exists():
            print(
                f"[GlobalDataset] Cache missing: "
                f"{path}"
            )
            return None

        try:

            # yfinance CSV normally contains
            # two header rows.
            df = pd.read_csv(
                path,
                header=[0, 1],
            )

            # Flatten MultiIndex columns.
            if isinstance(df.columns, pd.MultiIndex):

                df.columns = [
                    str(column[0])
                    for column in df.columns
                ]

            else:

                df.columns = [
                    str(column)
                    for column in df.columns
                ]

            # Remove duplicate columns.
            df = df.loc[
                :,
                ~df.columns.duplicated()
            ]

            if "Date" in df.columns:

                df["Date"] = pd.to_datetime(
                    df["Date"],
                    errors="coerce",
                )

                df = df.set_index("Date")

            required = [
                "Open",
                "High",
                "Low",
                "Close",
                "Volume",
            ]

            missing = [
                column
                for column in required
                if column not in df.columns
            ]

            if missing:

                raise ValueError(
                    f"Missing OHLCV columns: {missing}"
                )

            for column in required:

                df[column] = pd.to_numeric(
                    df[column],
                    errors="coerce",
                )

            df = df.dropna(
                subset=required
            )

            if df.empty:
                return None

            return df

        except Exception as exc:

            print(
                f"[GlobalDataset] Failed reading "
                f"{symbol}: {exc}"
            )

            return None

    def build(
        self,
        symbols=None,
        period="2y",
        interval="1d",
    ):

        symbols = (
            symbols
            if symbols is not None
            else self.DEFAULT_SYMBOLS
        )

        datasets = []

        for symbol in symbols:

            print()
            print(
                f"[GlobalDataset] Loading {symbol}..."
            )

            df = self._load_cached_data(
                symbol
            )

            if df is None:

                print(
                    f"[GlobalDataset] No cached "
                    f"data for {symbol}"
                )

                continue

            try:

                # =================================================
                # 1. TECHNICAL + PRICE ACTION FEATURES
                # =================================================

                df = Indicators.calculate(df)

                # =================================================
                # 2. OUTCOME-BASED LABELS
                # =================================================

                df = LabelBuilder.build(df)

                # =================================================
                # 3. ML DATASET VALIDATION
                # =================================================

                df = self.builder.prepare(df)

            except Exception as exc:

                print(
                    f"[GlobalDataset] Failed "
                    f"{symbol}: {exc}"
                )

                continue

            df = df.copy()

            df["SYMBOL"] = symbol

            datasets.append(df)

            print(
                f"[GlobalDataset] {symbol}: "
                f"{len(df)} rows"
            )

        if not datasets:

            return None

        global_df = pd.concat(
            datasets,
            ignore_index=True,
        )

        global_df = (
            global_df
            .replace(
                [float("inf"), float("-inf")],
                pd.NA,
            )
            .dropna(
                subset=[
                    *self.builder.FEATURE_COLUMNS,
                    "LABEL",
                    "TRADE_RETURN",
                ],
            )
            .reset_index(drop=True)
        )

        print()
        print("==============================")
        print("GLOBAL DATASET")
        print("==============================")

        print(
            "rows:",
            len(global_df),
        )

        print(
            "stocks:",
            global_df["SYMBOL"].nunique(),
        )

        print()

        print(
            global_df["SYMBOL"]
            .value_counts()
        )

        print()

        print("labels:")

        print(
            global_df["LABEL"]
            .value_counts()
            .sort_index()
        )

        return global_df
