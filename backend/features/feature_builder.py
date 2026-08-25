import numpy as np

from backend.features.indicators import Indicators
from backend.features.label_builder import LabelBuilder


class FeatureBuilder:

    @staticmethod
    def build(df):

        df = df.copy()

        # =====================================================
        # 1. Validate required market columns
        # =====================================================

        required_columns = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
        ]

        missing = [
            column
            for column in required_columns
            if column not in df.columns
        ]

        if missing:
            raise ValueError(
                f"Missing required market columns: {missing}"
            )

        # =====================================================
        # 2. Calculate technical + candlestick features
        # =====================================================

        df = Indicators.calculate(df)

        # =====================================================
        # 3. Generate labels
        # =====================================================

        df = LabelBuilder.build(df)

        # =====================================================
        # 4. Replace infinite numerical values
        #
        # Do NOT drop rows yet.
        # =====================================================

        numeric_columns = df.select_dtypes(
            include=[np.number]
        ).columns

        df[numeric_columns] = (
            df[numeric_columns]
            .replace([np.inf, -np.inf], np.nan)
        )

        return df