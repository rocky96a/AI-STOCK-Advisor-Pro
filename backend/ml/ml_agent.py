"""
Unified ML Agent.

Current version:
- supervised Random Forest
- walk-forward validation
- UP / DOWN probabilities
- expected price range using ATR + model probability
- clean single MLAgent implementation

Unsupervised regime detection and multi-model ensemble
will be added after this baseline is stable.
"""

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score

from backend.indicators import trend, momentum, volatility, volume
from backend.ml.feature_engineering import build_training_set


MIN_TRAINING_ROWS = 150

REQUIRED_COLUMNS = [
    "RSI",
    "MACD",
    "MACD_SIGNAL",
    "ADX",
    "CCI",
    "EMA9",
    "EMA20",
    "EMA50",
    "EMA100",
    "EMA200",
    "ATR",
    "CMF",
    "OBV",
]


def _ensure_indicators(df):
    """Ensure the dataframe contains all required indicators."""

    missing = [
        col for col in REQUIRED_COLUMNS
        if col not in df.columns
    ]

    if not missing:
        return df

    df = df.copy()

    df = trend.calculate(df)
    df = momentum.calculate(df)
    df = volatility.calculate(df)
    df = volume.calculate(df)

    return df


class MLAgent:

    @staticmethod
    def predict(
        df,
        horizon=5,
        atr_threshold=1.0,
    ):
        """
        Predict probability of a clean UP/DOWN move.

        horizon:
            Number of candles ahead.

        atr_threshold:
            Required move in ATR multiples for training labels.
        """

        if df is None or len(df) < MIN_TRAINING_ROWS:
            return {
                "available": False,
                "reason": "Insufficient historical data.",
            }

        try:
            df = _ensure_indicators(df)

            X, y, live_row = build_training_set(
                df,
                horizon=horizon,
                atr_threshold=atr_threshold,
            )

        except Exception as exc:
            return {
                "available": False,
                "reason": f"Feature engineering failed: {exc}",
            }

        if len(X) < MIN_TRAINING_ROWS:
            return {
                "available": False,
                "reason": (
                    f"Not enough usable training rows "
                    f"({len(X)}; need {MIN_TRAINING_ROWS}+)."
                ),
            }

        if y.nunique() < 2:
            return {
                "available": False,
                "reason": (
                    "Training data does not contain both "
                    "UP and DOWN examples."
                ),
            }

        # -----------------------------------------
        # Walk-forward validation
        # -----------------------------------------

        splitter = TimeSeriesSplit(n_splits=5)

        validation_scores = []

        for train_idx, test_idx in splitter.split(X):

            model = RandomForestClassifier(
                n_estimators=200,
                max_depth=6,
                min_samples_leaf=10,
                random_state=42,
                n_jobs=-1,
                class_weight="balanced",
            )

            model.fit(
                X.iloc[train_idx],
                y.iloc[train_idx],
            )

            predictions = model.predict(
                X.iloc[test_idx]
            )

            validation_scores.append(
                accuracy_score(
                    y.iloc[test_idx],
                    predictions,
                )
            )

        validation_accuracy = float(
            np.mean(validation_scores)
        )

        # -----------------------------------------
        # Final model
        # -----------------------------------------

        final_model = RandomForestClassifier(
            n_estimators=300,
            max_depth=6,
            min_samples_leaf=10,
            random_state=42,
            n_jobs=-1,
            class_weight="balanced",
        )

        final_model.fit(X, y)

        probabilities = final_model.predict_proba(
            live_row
        )[0]

        classes = list(
            final_model.classes_
        )

        up_probability = (
            float(
                probabilities[
                    classes.index(1)
                ]
            )
            if 1 in classes
            else 0.0
        )

        down_probability = (
            float(
                probabilities[
                    classes.index(0)
                ]
            )
            if 0 in classes
            else 0.0
        )

        direction = (
            "UP"
            if up_probability >= down_probability
            else "DOWN"
        )

        confidence = max(
            up_probability,
            down_probability,
        )

        # -----------------------------------------
        # Current price / volatility
        # -----------------------------------------

        current_price = float(
            df["Close"].iloc[-1]
        )

        atr = float(
            df["ATR"].iloc[-1]
        )

        atr_percent = (
            atr / current_price * 100
            if current_price
            else 0
        )

        # -----------------------------------------
        # Expected price range
        #
        # This is NOT a guaranteed target.
        # It is an ATR-based probabilistic range.
        # -----------------------------------------

        lower_bound = current_price - atr
        upper_bound = current_price + atr

        # Directional adjustment:
        # stronger probability pushes the expected
        # center slightly toward that direction.
        directional_edge = (
            up_probability - down_probability
        )

        expected_price = (
            current_price
            + directional_edge * atr
        )

        # -----------------------------------------
        # Feature importance
        # -----------------------------------------

        importances = sorted(
            zip(
                X.columns,
                final_model.feature_importances_,
            ),
            key=lambda item: item[1],
            reverse=True,
        )[:5]

        top_features = [
            {
                "feature": feature,
                "importance": round(
                    float(importance),
                    3,
                ),
            }
            for feature, importance
            in importances
        ]

        return {
            "available": True,

            "direction": direction,

            "up_probability": round(
                up_probability * 100,
                1,
            ),

            "down_probability": round(
                down_probability * 100,
                1,
            ),

            "confidence": round(
                confidence * 100,
                1,
            ),

            "validation_accuracy": round(
                validation_accuracy * 100,
                1,
            ),

            "horizon_candles": horizon,

            "training_rows": len(X),

            "price": round(
                current_price,
                2,
            ),

            "expected_price": round(
                expected_price,
                2,
            ),

            "price_range": {
                "lower": round(
                    lower_bound,
                    2,
                ),
                "upper": round(
                    upper_bound,
                    2,
                ),
                "width": round(
                    upper_bound - lower_bound,
                    2,
                ),
                "atr": round(
                    atr,
                    2,
                ),
                "atr_percent": round(
                    atr_percent,
                    2,
                ),
            },

            "top_features": top_features,

            "caveat": (
                "ML probability is an estimate based on "
                "historical patterns. It is not a guarantee "
                "of future price movement."
            ),
        }
