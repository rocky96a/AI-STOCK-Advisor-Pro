class FinBERT:
    _model = None
    _error = None

    @classmethod
    def load(cls):
        if cls._model is not None:
            return cls._model

        if cls._error is not None:
            raise RuntimeError(cls._error)

        try:
            from transformers import pipeline

            cls._model = pipeline(
                "text-classification",
                model="ProsusAI/finbert",
                tokenizer="ProsusAI/finbert",
                truncation=True,
            )
            return cls._model
        except Exception as exc:
            cls._error = (
                "FinBERT is unavailable. Install transformers/torch "
                f"and ensure the model can be downloaded: {exc}"
            )
            raise RuntimeError(cls._error)
