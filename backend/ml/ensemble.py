from backend.ml.model_manager import ModelManager


class EnsemblePredictor:

    MODELS = [

        "random_forest",

        "xgboost",

        "lightgbm",
         "lstm"

    ]

    WEIGHTS = {

        "random_forest":0.30,

        "xgboost":0.40,

        "lightgbm":0.30,
        "lstm":0.25

    }

    @classmethod
    def predict(cls, X):

        pass