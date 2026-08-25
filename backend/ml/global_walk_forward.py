from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
)

from backend.ml.global_dataset import GlobalDatasetBuilder


# ============================================================
# CONFIGURATION
# ============================================================

N_SPLITS = 5

MIN_TRAIN_DATES = 120

TEST_DATES = 30


# ============================================================
# GLOBAL WALK-FORWARD VALIDATION
# ============================================================

class GlobalWalkForwardValidator:

    def __init__(
        self,
        n_splits=N_SPLITS,
        min_train_dates=MIN_TRAIN_DATES,
        test_dates=TEST_DATES,
    ):

        self.n_splits = n_splits
        self.min_train_dates = min_train_dates
        self.test_dates = test_dates

        self.builder = GlobalDatasetBuilder()

    # ========================================================
    # BUILD DATASET
    # ========================================================

    def load_dataset(
        self,
        symbols=None,
        period="2y",
        interval="1d",
    ):

        df = self.builder.build(
            symbols=symbols,
            period=period,
            interval=interval,
        )

        if df is None or df.empty:
            raise ValueError(
                "Global dataset is empty."
            )

        if "Date" not in df.columns:
            raise ValueError(
                "Global dataset does not contain Date."
            )

        # ----------------------------------------------------
        # Normalize Date
        # ----------------------------------------------------

        df = df.copy()

        df["Date"] = pd.to_datetime(
            df["Date"],
            errors="coerce",
        )

        df = df.dropna(
            subset=["Date"]
        ).copy()

        # ----------------------------------------------------
        # Sort chronologically
        # ----------------------------------------------------

        df = (
            df.sort_values(
                by=["Date", "SYMBOL"]
            )
            .reset_index(drop=True)
        )

        return df

    # ========================================================
    # CREATE WALK-FORWARD FOLDS
    # ========================================================

    def create_folds(self, df):

        unique_dates = (
            df["Date"]
            .drop_duplicates()
            .sort_values()
            .reset_index(drop=True)
        )

        total_dates = len(unique_dates)

        if total_dates <= self.min_train_dates:
            raise ValueError(
                "Not enough dates for "
                "walk-forward validation."
            )

        folds = []

        # ----------------------------------------------------
        # Determine possible test windows
        # ----------------------------------------------------

        available_test_dates = (
            total_dates - self.min_train_dates
        )

        if available_test_dates < self.test_dates:
            raise ValueError(
                "Not enough dates for requested "
                "walk-forward test window."
            )

        max_possible_folds = (
            available_test_dates
            // self.test_dates
        )

        actual_splits = min(
            self.n_splits,
            max_possible_folds,
        )

        # ----------------------------------------------------
        # Create expanding-window folds
        # ----------------------------------------------------

        for fold_number in range(
            actual_splits
        ):

            train_end_index = (
                self.min_train_dates
                + fold_number * self.test_dates
                - 1
            )

            test_start_index = (
                train_end_index + 1
            )

            test_end_index = min(
                test_start_index
                + self.test_dates
                - 1,
                total_dates - 1,
            )

            if test_start_index >= total_dates:
                break

            train_end_date = (
                unique_dates.iloc[
                    train_end_index
                ]
            )

            test_start_date = (
                unique_dates.iloc[
                    test_start_index
                ]
            )

            test_end_date = (
                unique_dates.iloc[
                    test_end_index
                ]
            )

            train_mask = (
                df["Date"]
                <= train_end_date
            )

            test_mask = (
                (df["Date"] >= test_start_date)
                &
                (df["Date"] <= test_end_date)
            )

            train_df = (
                df.loc[train_mask]
                .copy()
            )

            test_df = (
                df.loc[test_mask]
                .copy()
            )

            if train_df.empty:
                continue

            if test_df.empty:
                continue

            folds.append(
                {
                    "fold": fold_number + 1,
                    "train_df": train_df,
                    "test_df": test_df,
                    "train_start": train_df["Date"].min(),
                    "train_end": train_df["Date"].max(),
                    "test_start": test_df["Date"].min(),
                    "test_end": test_df["Date"].max(),
                }
            )

        return folds

    # ========================================================
    # TRAIN ONE FOLD
    # ========================================================

    def run_fold(
        self,
        fold,
        feature_columns,
    ):

        train_df = fold["train_df"]
        test_df = fold["test_df"]

        X_train = train_df[
            feature_columns
        ]

        y_train = (
            train_df["LABEL"]
            .astype(int)
        )

        X_test = test_df[
            feature_columns
        ]

        y_test = (
            test_df["LABEL"]
            .astype(int)
        )

        # ----------------------------------------------------
        # Check classes
        # ----------------------------------------------------

        if y_train.nunique() < 2:

            return {
                "fold": fold["fold"],
                "status": "SKIPPED",
                "reason": (
                    "Training data contains "
                    "fewer than two classes."
                ),
            }

        if y_test.empty:

            return {
                "fold": fold["fold"],
                "status": "SKIPPED",
                "reason": "Test data is empty.",
            }

        # ----------------------------------------------------
        # Train RF
        # ----------------------------------------------------

        model = RandomForestClassifier(
            n_estimators=400,
            max_depth=10,
            min_samples_leaf=5,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )

        model.fit(
            X_train,
            y_train,
        )

        # ----------------------------------------------------
        # Predict
        # ----------------------------------------------------

        predictions = model.predict(
            X_test
        )

        # ----------------------------------------------------
        # Metrics
        # ----------------------------------------------------

        accuracy = accuracy_score(
            y_test,
            predictions,
        )

        balanced_accuracy = (
            balanced_accuracy_score(
                y_test,
                predictions,
            )
        )

        precision = precision_score(
            y_test,
            predictions,
            labels=[0, 1, 2],
            average="weighted",
            zero_division=0,
        )

        recall = recall_score(
            y_test,
            predictions,
            labels=[0, 1, 2],
            average="weighted",
            zero_division=0,
        )

        f1 = f1_score(
            y_test,
            predictions,
            labels=[0, 1, 2],
            average="weighted",
            zero_division=0,
        )

        return {
            "fold": fold["fold"],
            "status": "OK",

            "train_rows": len(train_df),
            "test_rows": len(test_df),

            "train_stocks": int(
                train_df["SYMBOL"].nunique()
            ),

            "test_stocks": int(
                test_df["SYMBOL"].nunique()
            ),

            "train_start": str(
                fold["train_start"]
            ),

            "train_end": str(
                fold["train_end"]
            ),

            "test_start": str(
                fold["test_start"]
            ),

            "test_end": str(
                fold["test_end"]
            ),

            "accuracy": round(
                accuracy * 100,
                2,
            ),

            "balanced_accuracy": round(
                balanced_accuracy * 100,
                2,
            ),

            "precision": round(
                precision * 100,
                2,
            ),

            "recall": round(
                recall * 100,
                2,
            ),

            "f1": round(
                f1 * 100,
                2,
            ),
        }

    # ========================================================
    # RUN VALIDATION
    # ========================================================

    def validate(
        self,
        symbols=None,
        period="2y",
        interval="1d",
    ):

        print()
        print("==============================")
        print("GLOBAL WALK-FORWARD")
        print("==============================")

        # ----------------------------------------------------
        # Load
        # ----------------------------------------------------

        df = self.load_dataset(
            symbols=symbols,
            period=period,
            interval=interval,
        )

        feature_columns = (
            self.builder.builder.FEATURE_COLUMNS
        )

        print(
            "Rows:",
            len(df),
        )

        print(
            "Stocks:",
            df["SYMBOL"].nunique(),
        )

        print(
            "Dates:",
            df["Date"].nunique(),
        )

        print(
            "Start:",
            df["Date"].min(),
        )

        print(
            "End:",
            df["Date"].max(),
        )

        # ----------------------------------------------------
        # Create folds
        # ----------------------------------------------------

        folds = self.create_folds(
            df
        )

        print()
        print(
            "Folds:",
            len(folds),
        )

        # ----------------------------------------------------
        # Run folds
        # ----------------------------------------------------

        results = []

        for fold in folds:

            print()
            print(
                "------------------------------"
            )

            print(
                f"FOLD {fold['fold']}"
            )

            print(
                "Train:",
                fold["train_start"],
                "→",
                fold["train_end"],
            )

            print(
                "Test:",
                fold["test_start"],
                "→",
                fold["test_end"],
            )

            result = self.run_fold(
                fold,
                feature_columns,
            )

            results.append(
                result
            )

            print(
                result
            )

        # ----------------------------------------------------
        # Successful folds
        # ----------------------------------------------------

        valid_results = [
            result
            for result in results
            if result.get("status") == "OK"
        ]

        if not valid_results:

            return {
                "success": False,
                "message": (
                    "No valid walk-forward "
                    "folds were completed."
                ),
                "folds": results,
            }

        # ----------------------------------------------------
        # Aggregate metrics
        # ----------------------------------------------------

        metrics = [
            "accuracy",
            "balanced_accuracy",
            "precision",
            "recall",
            "f1",
        ]

        averages = {}

        for metric in metrics:

            values = [
                result[metric]
                for result in valid_results
            ]

            averages[metric] = round(
                float(
                    np.mean(values)
                ),
                2,
            )

        # ----------------------------------------------------
        # Print summary
        # ----------------------------------------------------

        print()
        print("==============================")
        print("WALK-FORWARD SUMMARY")
        print("==============================")

        for metric, value in averages.items():

            print(
                f"{metric}: {value}%"
            )

        return {
            "success": True,
            "folds_completed": len(
                valid_results
            ),
            "fold_results": results,
            "average_metrics": averages,
        }


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    validator = (
        GlobalWalkForwardValidator(
            n_splits=5,
            min_train_dates=120,
            test_dates=30,
        )
    )

    result = validator.validate(
        symbols=[
            "TCS.NS",
            "INFY.NS",
            "HDFCBANK.NS",
            "ICICIBANK.NS",
            "AXISBANK.NS",
            "LT.NS",
        ],
        period="2y",
        interval="1d",
    )

    print()
    print("==============================")
    print("FINAL RESULT")
    print("==============================")

    for key, value in result.items():

        print(
            f"{key}: {value}"
        )
