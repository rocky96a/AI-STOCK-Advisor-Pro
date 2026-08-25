from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)

from backend.ml.global_dataset import GlobalDatasetBuilder


MODEL_PATH = (
    Path(__file__).resolve().parent
    / "models"
    / "global_random_forest.pkl"
)

TRAIN_RATIO = 0.80


def train_global_model(
    symbols=None,
    period="2y",
    interval="1d",
):
    builder = GlobalDatasetBuilder()

    df = builder.build(
        symbols=symbols,
        period=period,
        interval=interval,
    )

    if df is None or df.empty:
        return {
            "success": False,
            "message": "Global dataset is empty.",
        }

    # =========================================================
    # 1. CHECK DATE COLUMN
    # =========================================================

    if "Date" not in df.columns:
        return {
            "success": False,
            "message": (
                "Global dataset must contain "
                "a Date column for chronological splitting."
            ),
        }

    # =========================================================
    # 2. NORMALIZE DATE
    # =========================================================

    df = df.copy()

    df["Date"] = pd.to_datetime(
        df["Date"],
        errors="coerce",
    )

    before_date = len(df)

    df = df.dropna(
        subset=["Date"]
    ).copy()

    if df.empty:
        return {
            "success": False,
            "message": "No valid dates remain in global dataset.",
        }

    print(
        f"[GlobalTrain] Date filtering: "
        f"{before_date} -> {len(df)} rows"
    )

    # =========================================================
    # 3. SORT BY DATE
    # =========================================================

    df = (
        df.sort_values(
            by=["Date", "SYMBOL"],
            ascending=[True, True],
        )
        .reset_index(drop=True)
    )

    # =========================================================
    # 4. GET UNIQUE CHRONOLOGICAL DATES
    # =========================================================

    unique_dates = (
        df["Date"]
        .drop_duplicates()
        .sort_values()
        .reset_index(drop=True)
    )

    if len(unique_dates) < 2:
        return {
            "success": False,
            "message": (
                "Not enough unique dates "
                "for chronological train/test split."
            ),
        }

    # =========================================================
    # 5. DATE-BASED 80/20 SPLIT
    # =========================================================

    split_date_index = int(
        len(unique_dates) * TRAIN_RATIO
    )

    # Make sure both sides contain at least one date.
    split_date_index = max(
        1,
        min(
            split_date_index,
            len(unique_dates) - 1,
        ),
    )

    train_end_date = unique_dates.iloc[
        split_date_index - 1
    ]

    test_start_date = unique_dates.iloc[
        split_date_index
    ]

    print()
    print("==============================")
    print("GLOBAL DATE SPLIT")
    print("==============================")
    print(
        "First date:",
        df["Date"].min(),
    )
    print(
        "Last date:",
        df["Date"].max(),
    )
    print(
        "Unique dates:",
        len(unique_dates),
    )
    print(
        "Train end date:",
        train_end_date,
    )
    print(
        "Test start date:",
        test_start_date,
    )

    # =========================================================
    # 6. BUILD TRAIN / TEST DATASETS
    # =========================================================

    train_mask = (
        df["Date"] <= train_end_date
    )

    test_mask = (
        df["Date"] >= test_start_date
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
        return {
            "success": False,
            "message": "Training dataset is empty.",
        }

    if test_df.empty:
        return {
            "success": False,
            "message": "Testing dataset is empty.",
        }

    # =========================================================
    # 7. FEATURES
    # =========================================================

    feature_columns = (
        builder.builder.FEATURE_COLUMNS
    )

    X_train = train_df[
        feature_columns
    ].copy()

    X_test = test_df[
        feature_columns
    ].copy()

    y_train = (
        train_df["LABEL"]
        .astype(int)
        .copy()
    )

    y_test = (
        test_df["LABEL"]
        .astype(int)
        .copy()
    )

    # =========================================================
    # 8. BASIC VALIDATION
    # =========================================================

    if len(X_train) < 100:
        return {
            "success": False,
            "message": (
                "Training set is too small."
            ),
        }

    if len(X_test) == 0:
        return {
            "success": False,
            "message": (
                "Testing set is empty."
            ),
        }

    if y_train.nunique() < 2:
        return {
            "success": False,
            "message": (
                "Training set contains "
                "fewer than two classes."
            ),
        }

    # =========================================================
    # 9. TRAIN VALIDATION MODEL
    # =========================================================

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

    # =========================================================
    # 10. OUT-OF-SAMPLE TEST
    # =========================================================

    predictions = model.predict(
        X_test
    )

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

    matrix = confusion_matrix(
        y_test,
        predictions,
        labels=[0, 1, 2],
    )

    # =========================================================
    # 11. RETRAIN FINAL MODEL ON ALL DATA
    # =========================================================

    X_all = df[
        feature_columns
    ].copy()

    y_all = (
        df["LABEL"]
        .astype(int)
        .copy()
    )

    final_model = RandomForestClassifier(
        n_estimators=400,
        max_depth=10,
        min_samples_leaf=5,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    final_model.fit(
        X_all,
        y_all,
    )

    # =========================================================
    # 12. SAVE MODEL
    # =========================================================

    MODEL_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        final_model,
        MODEL_PATH,
    )

    # =========================================================
    # 13. REPORT
    # =========================================================

    return {
        "success": True,
        "model_path": str(MODEL_PATH),

        "rows": len(df),

        "stocks": int(
            df["SYMBOL"].nunique()
        ),

        "train_rows": len(train_df),

        "test_rows": len(test_df),

        "unique_dates": len(unique_dates),

        "train_start_date": str(
            train_df["Date"].min()
        ),

        "train_end_date": str(
            train_df["Date"].max()
        ),

        "test_start_date": str(
            test_df["Date"].min()
        ),

        "test_end_date": str(
            test_df["Date"].max()
        ),

        "accuracy": round(
            float(
                accuracy * 100
            ),
            2,
        ),

        "balanced_accuracy": round(
            float(
                balanced_accuracy * 100
            ),
            2,
        ),

        "precision": round(
            float(
                precision * 100
            ),
            2,
        ),

        "recall": round(
            float(
                recall * 100
            ),
            2,
        ),

        "f1": round(
            float(
                f1 * 100
            ),
            2,
        ),

        "confusion_matrix": (
            matrix
            .astype(int)
            .tolist()
        ),

        "label_distribution": {
            str(int(label)): int(
                np.sum(
                    y_all == label
                )
            )
            for label in [0, 1, 2]
        },

        "train_label_distribution": {
            str(int(label)): int(
                np.sum(
                    y_train == label
                )
            )
            for label in [0, 1, 2]
        },

        "test_label_distribution": {
            str(int(label)): int(
                np.sum(
                    y_test == label
                )
            )
            for label in [0, 1, 2]
        },
    }


if __name__ == "__main__":

    result = train_global_model(
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
    print("GLOBAL MODEL RESULT")
    print("==============================")

    for key, value in result.items():
        print(
            f"{key}: {value}"
        )