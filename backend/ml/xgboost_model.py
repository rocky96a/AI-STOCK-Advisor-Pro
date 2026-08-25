from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score
)

from xgboost import XGBClassifier

from backend.ml.dataset import DatasetBuilder
from backend.ml.model_manager import ModelManager


class XGBoostTrainer:

    MODEL_NAME = "xgboost"

    @classmethod
    def train(cls, symbol):

        builder = DatasetBuilder()

        X, y = builder.get_features(symbol)

        if X is None:

            return {

                "success": False,

                "message": "Dataset unavailable"

            }

        X_train, X_test, y_train, y_test = train_test_split(

            X,
            y,

            test_size=0.2,

            shuffle=False

        )

        model = XGBClassifier(

            n_estimators=300,

            learning_rate=0.05,

            max_depth=6,

            subsample=0.9,

            colsample_bytree=0.9,

            objective="multi:softprob",

            num_class=3,

            eval_metric="mlogloss",

            random_state=42

        )

        model.fit(

            X_train,
            y_train

        )

        prediction = model.predict(

            X_test

        )

        manager = ModelManager()

        manager.save(

            model,

            cls.MODEL_NAME

        )

        return {

            "success": True,

            "model": "XGBoost",

            "accuracy": round(

                accuracy_score(

                    y_test,

                    prediction

                ) * 100,

                2

            ),

            "precision": round(

                precision_score(

                    y_test,

                    prediction,

                    average="weighted",

                    zero_division=0

                ) * 100,

                2

            ),

            "recall": round(

                recall_score(

                    y_test,

                    prediction,

                    average="weighted",

                    zero_division=0

                ) * 100,

                2

            ),

            "f1": round(

                f1_score(

                    y_test,

                    prediction,

                    average="weighted",

                    zero_division=0

                ) * 100,

                2

            ),

            "samples": len(X)

        }