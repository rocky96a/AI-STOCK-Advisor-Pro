import os
import joblib
from pathlib import Path


class ModelManager:

    MODEL_DIR = Path(__file__).resolve().parent / "models"

    MODELS = {
        "random_forest": "random_forest.pkl",
        "xgboost": "xgboost.pkl",
        "lightgbm": "lightgbm.pkl",
        "lstm": "lstm.keras",
        "transformer": "transformer.keras",
    }

    def __init__(self):
        self.MODEL_DIR.mkdir(
            exist_ok=True
        )

    @staticmethod
    def _safe_symbol(symbol):
        return (
            str(symbol)
            .strip()
            .upper()
            .replace(".", "_")
            .replace("/", "_")
            .replace("\\", "_")
            .replace(" ", "_")
        )

    def get_path(
        self,
        model_name,
        symbol=None,
    ):

        filename = self.MODELS.get(model_name)

        if filename is None:
            raise ValueError(
                f"Unknown model {model_name}"
            )

        if symbol:
            stem = Path(filename).stem
            suffix = Path(filename).suffix

            filename = (
                f"{stem}_"
                f"{self._safe_symbol(symbol)}"
                f"{suffix}"
            )

        return self.MODEL_DIR / filename

    def save(
        self,
        model,
        model_name,
        symbol=None,
    ):

        path = self.get_path(
            model_name,
            symbol,
        )

        joblib.dump(
            model,
            path,
        )

        return str(path)

    def load(
        self,
        model_name,
        symbol=None,
    ):

        path = self.get_path(
            model_name,
            symbol,
        )

        if not path.exists():
            return None

        return joblib.load(path)

    def exists(
        self,
        model_name,
        symbol=None,
    ):

        return self.get_path(
            model_name,
            symbol,
        ).exists()

    def delete(
        self,
        model_name,
        symbol=None,
    ):

        path = self.get_path(
            model_name,
            symbol,
        )

        if path.exists():
            os.remove(path)

    def list_models(self):

        models = []

        for model_name in self.MODELS:

            models.append({
                "name": model_name,
                "exists": self.exists(
                    model_name
                ),
                "path": str(
                    self.get_path(
                        model_name
                    )
                ),
            })

        return models