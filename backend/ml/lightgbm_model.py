from lightgbm import LGBMClassifier

class LightGBMTrainer:

    MODEL_NAME = "lightgbm"

    @classmethod
    def train(cls, X_train, y_train):

        model = LGBMClassifier(

            n_estimators=300,

            learning_rate=0.05,

            max_depth=8,

            num_leaves=31,

            subsample=0.9,

            colsample_bytree=0.9,

            random_state=42

        )

        model.fit(

            X_train,

            y_train

        )

        return model