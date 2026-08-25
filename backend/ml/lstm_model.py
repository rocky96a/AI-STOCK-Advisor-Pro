

from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping

from backend.ml.model_manager import ModelManager
import numpy as np
import tensorflow as tf



class LSTMTrainer:

    MODEL_NAME = "lstm"

    WINDOW = 30

    @staticmethod
    def build_model(input_shape):

        model = Sequential()

        model.add(
            LSTM(
                64,
                return_sequences=True,
                input_shape=input_shape
            )
        )

        model.add(Dropout(0.2))

        model.add(LSTM(32))

        model.add(Dropout(0.2))

        model.add(Dense(16, activation="relu"))

        model.add(Dense(3, activation="softmax"))

        model.compile(

            optimizer="adam",

            loss="sparse_categorical_crossentropy",

            metrics=["accuracy"]

        )

        return model