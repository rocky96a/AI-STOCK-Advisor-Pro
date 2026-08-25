import numpy as np
import pandas as pd


class DatasetBuilder:

    # =========================================================
    # ML FEATURE SCHEMA
    # =========================================================

    FEATURE_COLUMNS = [

        # -----------------------------------------------------
        # Price / Volume
        # -----------------------------------------------------
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",

        # -----------------------------------------------------
        # Technical Indicators
        # -----------------------------------------------------
        "RSI",
        "MACD",
        "MACD_SIGNAL",
        "EMA20",
        "EMA50",
        "EMA200",
        "ATR",
        "BB_UPPER",
        "BB_LOWER",
        "ADX",
        "OBV",

        # -----------------------------------------------------
        # Candle Structure
        # -----------------------------------------------------
        "CANDLE_BODY",
        "CANDLE_RANGE",
        "UPPER_WICK",
        "LOWER_WICK",
        "BODY_RATIO",
        "UPPER_WICK_RATIO",
        "LOWER_WICK_RATIO",
        "CANDLE_DIRECTION",

        # -----------------------------------------------------
        # Candlestick Patterns
        # -----------------------------------------------------
        "DOJI",
        "HAMMER",
        "INVERTED_HAMMER",
        "SHOOTING_STAR",
        "HANGING_MAN",
        "BULLISH_ENGULFING",
        "BEARISH_ENGULFING",
        "MORNING_STAR",
        "EVENING_STAR",
    ]

    TARGET_COLUMN = "LABEL"

    RETURN_COLUMN = "TRADE_RETURN"

    VALID_COLUMN = "LABEL_VALID"

    # =========================================================
    # PREPARE DATASET
    # =========================================================

    @classmethod
    def prepare(cls, df):

        if df is None:
            raise ValueError(
                "DatasetBuilder.prepare() received None"
            )

        if not isinstance(df, pd.DataFrame):
            raise TypeError(
                "DatasetBuilder.prepare() expects a pandas DataFrame"
            )

        df = df.copy()

        if df.empty:
            raise ValueError(
                "DatasetBuilder received an empty DataFrame"
            )

        # =====================================================
        # 1. CHECK FEATURE COLUMNS
        # =====================================================

        missing_features = [
            column
            for column in cls.FEATURE_COLUMNS
            if column not in df.columns
        ]

        if missing_features:

            raise ValueError(
                "Missing ML features: "
                f"{missing_features}"
            )

        # =====================================================
        # 2. CHECK TARGET
        # =====================================================

        if cls.TARGET_COLUMN not in df.columns:

            raise ValueError(
                "LABEL column is missing"
            )

        # =====================================================
        # 3. LABEL_VALID FILTER
        # =====================================================

        if cls.VALID_COLUMN in df.columns:

            valid_mask = (
                df[cls.VALID_COLUMN]
                .fillna(False)
                .astype(bool)
            )

            df = df.loc[valid_mask].copy()

        if df.empty:

            raise ValueError(
                "No rows remain after LABEL_VALID filtering"
            )

        # =====================================================
        # 4. CONVERT FEATURES TO NUMERIC
        # =====================================================

        for column in cls.FEATURE_COLUMNS:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

        # =====================================================
        # 5. REPLACE INFINITY
        # =====================================================

        df[cls.FEATURE_COLUMNS] = (
            df[cls.FEATURE_COLUMNS]
            .replace(
                [np.inf, -np.inf],
                np.nan
            )
        )

        # =====================================================
        # 6. REMOVE INVALID FEATURE ROWS
        # =====================================================

        before_features = len(df)

        df = df.dropna(
            subset=cls.FEATURE_COLUMNS
        ).copy()

        after_features = len(df)

        print(
            "[DatasetBuilder] "
            f"Feature NaN filtering: "
            f"{before_features} -> {after_features} rows"
        )

        if df.empty:

            raise ValueError(
                "No valid rows remain after "
                "feature NaN filtering"
            )

        # =====================================================
        # 7. CLEAN LABEL
        # =====================================================

        df[cls.TARGET_COLUMN] = pd.to_numeric(
            df[cls.TARGET_COLUMN],
            errors="coerce"
        )

        before_labels = len(df)

        df = df.dropna(
            subset=[cls.TARGET_COLUMN]
        ).copy()

        after_labels = len(df)

        print(
            "[DatasetBuilder] "
            f"LABEL NaN filtering: "
            f"{before_labels} -> {after_labels} rows"
        )

        if df.empty:

            raise ValueError(
                "No valid rows remain after "
                "LABEL filtering"
            )

        # =====================================================
        # 8. VALIDATE LABEL VALUES
        # =====================================================

        df[cls.TARGET_COLUMN] = (
            df[cls.TARGET_COLUMN]
            .astype(int)
        )

        unique_labels = sorted(
            df[cls.TARGET_COLUMN]
            .unique()
            .tolist()
        )

        print(
            "[DatasetBuilder] "
            f"Labels found: {unique_labels}"
        )

        # Do not silently modify unexpected labels.
        # Expected project labels are normally 0/1/2.
        invalid_labels = [
            label
            for label in unique_labels
            if label not in (0, 1, 2)
        ]

        if invalid_labels:

            raise ValueError(
                "Unexpected LABEL values: "
                f"{invalid_labels}. "
                "Expected labels: 0, 1, 2."
            )

        # =====================================================
        # 9. CLEAN TRADE_RETURN
        # =====================================================

        if cls.RETURN_COLUMN in df.columns:

            df[cls.RETURN_COLUMN] = (
                pd.to_numeric(
                    df[cls.RETURN_COLUMN],
                    errors="coerce"
                )
                .replace(
                    [np.inf, -np.inf],
                    np.nan
                )
                .fillna(0.0)
                .astype(float)
            )

        # =====================================================
        # 10. FINAL FEATURE NaN CHECK
        # =====================================================

        feature_nan = (
            df[cls.FEATURE_COLUMNS]
            .isna()
            .sum()
            .sum()
        )

        if feature_nan > 0:

            raise ValueError(
                "NaN values remain in ML features"
            )

        # =====================================================
        # 11. FINAL FEATURE INFINITY CHECK
        # =====================================================

        feature_values = (
            df[cls.FEATURE_COLUMNS]
            .to_numpy(dtype=float)
        )

        feature_inf = np.isinf(
            feature_values
        ).sum()

        if feature_inf > 0:

            raise ValueError(
                "Infinite values remain in ML features"
            )

        # =====================================================
        # 12. FINAL TARGET CHECK
        # =====================================================

        if df[cls.TARGET_COLUMN].isna().any():

            raise ValueError(
                "NaN values remain in LABEL"
            )

        # =====================================================
        # 13. FINAL INDEX CLEANUP
        # =====================================================

        df = df.reset_index(drop=True)

        print(
            "[DatasetBuilder] "
            f"Final dataset rows: {len(df)}"
        )

        print(
            "[DatasetBuilder] "
            f"Final feature count: "
            f"{len(cls.FEATURE_COLUMNS)}"
        )

        return df

    # =========================================================
    # BUILD X / Y
    # =========================================================

    @classmethod
    def build_xy(cls, df):

        df = cls.prepare(df)

        X = df[
            cls.FEATURE_COLUMNS
        ].copy()

        y = df[
            cls.TARGET_COLUMN
        ].copy()

        return X, y, df