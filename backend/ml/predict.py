import numpy as np
import pandas as pd

from backend.ml.model_manager import ModelManager
from backend.features.indicators import Indicators


class Predictor:

    DEFAULT_MODEL = "random_forest"

    FEATURE_COLUMNS = [

        "Open",
        "High",
        "Low",
        "Close",
        "Volume",

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

        "CANDLE_BODY",
        "CANDLE_RANGE",
        "UPPER_WICK",
        "LOWER_WICK",

        "BODY_RATIO",
        "UPPER_WICK_RATIO",
        "LOWER_WICK_RATIO",

        "CANDLE_DIRECTION",

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

    # ==========================================================
    # CANDLE ANALYSIS
    # ==========================================================

    @staticmethod
    def _candle_analysis(df):

        if df is None or df.empty:
            return {
                "total_candles": 0,
                "up_candles": 0,
                "down_candles": 0,
                "neutral_candles": 0,
                "up_percentage": 0.0,
                "down_percentage": 0.0,
                "neutral_percentage": 0.0,
                "current_up_streak": 0,
                "current_down_streak": 0,
                "last_5": [],
                "last_10": [],
            }

        work = df.copy()

        required = ["Open", "Close"]

        missing = [
            column
            for column in required
            if column not in work.columns
        ]

        if missing:
            return {
                "total_candles": 0,
                "up_candles": 0,
                "down_candles": 0,
                "neutral_candles": 0,
                "up_percentage": 0.0,
                "down_percentage": 0.0,
                "neutral_percentage": 0.0,
                "current_up_streak": 0,
                "current_down_streak": 0,
                "last_5": [],
                "last_10": [],
                "error": f"Missing columns: {missing}",
            }

        work["Open"] = pd.to_numeric(
            work["Open"],
            errors="coerce",
        )

        work["Close"] = pd.to_numeric(
            work["Close"],
            errors="coerce",
        )

        work = (
            work
            .dropna(subset=["Open", "Close"])
            .reset_index(drop=True)
        )

        if work.empty:
            return {
                "total_candles": 0,
                "up_candles": 0,
                "down_candles": 0,
                "neutral_candles": 0,
                "up_percentage": 0.0,
                "down_percentage": 0.0,
                "neutral_percentage": 0.0,
                "current_up_streak": 0,
                "current_down_streak": 0,
                "last_5": [],
                "last_10": [],
            }

        # ------------------------------------------------------
        # Determine candle direction
        # ------------------------------------------------------

        directions = []

        for _, row in work.iterrows():

            if row["Close"] > row["Open"]:
                directions.append("UP")

            elif row["Close"] < row["Open"]:
                directions.append("DOWN")

            else:
                directions.append("NEUTRAL")

        work["DIRECTION"] = directions

        total = len(directions)

        up_count = directions.count("UP")
        down_count = directions.count("DOWN")
        neutral_count = directions.count("NEUTRAL")

        # ------------------------------------------------------
        # Current UP streak
        # ------------------------------------------------------

        current_up_streak = 0

        for direction in reversed(directions):

            if direction == "UP":
                current_up_streak += 1
            else:
                break

        # ------------------------------------------------------
        # Current DOWN streak
        # ------------------------------------------------------

        current_down_streak = 0

        for direction in reversed(directions):

            if direction == "DOWN":
                current_down_streak += 1
            else:
                break

        # ------------------------------------------------------
        # Recent candles
        # ------------------------------------------------------

        recent_5 = directions[-5:]
        recent_10 = directions[-10:]

        arrow_map = {
            "UP": "↑",
            "DOWN": "↓",
            "NEUTRAL": "→",
        }

        last_5 = [
            {
                "direction": direction,
                "symbol": arrow_map[direction],
            }
            for direction in recent_5
        ]

        last_10 = [
            {
                "direction": direction,
                "symbol": arrow_map[direction],
            }
            for direction in recent_10
        ]

        # ------------------------------------------------------
        # Latest candle
        # ------------------------------------------------------

        latest_direction = directions[-1]

        # ------------------------------------------------------
        # Return candle statistics
        # ------------------------------------------------------

        return {

            "total_candles": total,

            "up_candles": up_count,

            "down_candles": down_count,

            "neutral_candles": neutral_count,

            "up_percentage": round(
                (up_count / total) * 100,
                2,
            ),

            "down_percentage": round(
                (down_count / total) * 100,
                2,
            ),

            "neutral_percentage": round(
                (neutral_count / total) * 100,
                2,
            ),

            "current_direction": latest_direction,

            "current_up_streak": current_up_streak,

            "current_down_streak": current_down_streak,

            "last_5": last_5,

            "last_10": last_10,
        }

    # ==========================================================
    # ML PREDICTION
    # ==========================================================

    @classmethod
    def predict(
        cls,
        df,
        symbol,
        model_name=None,
    ):

        if model_name is None:
            model_name = cls.DEFAULT_MODEL

        if df is None or df.empty:

            return {
                "available": False,
                "reason": "No market data.",
            }

        # ------------------------------------------------------
        # Candle analysis
        # ------------------------------------------------------

        candle_analysis = cls._candle_analysis(df)

        # ------------------------------------------------------
        # Load model
        # ------------------------------------------------------

        manager = ModelManager()

        # Prefer a symbol-specific model. If one is unavailable, use the
        # trained universal/global model. The global model uses the same
        # 33 feature columns and is explicitly intended for unseen symbols.
        model = manager.load(
            model_name,
            symbol=symbol,
        )
        model_source = "symbol"

        if model is None and model_name == "random_forest":
            global_path = manager.MODEL_DIR / "global_random_forest.pkl"
            if global_path.exists():
                try:
                    model = manager.load("random_forest", symbol=None)
                except Exception:
                    model = None

                # ModelManager's standard filename is random_forest.pkl;
                # the global model has its own filename, so load it directly.
                if model is None:
                    try:
                        import joblib
                        model = joblib.load(global_path)
                    except Exception:
                        model = None

                if model is not None:
                    model_source = "global"

        if model is None:
            return {
                "available": False,
                "reason": (
                    f"No trained {model_name} model exists for {symbol} "
                    "and no compatible global model is available."
                ),
            }

        # ------------------------------------------------------
        # Calculate live indicators
        # ------------------------------------------------------

        try:

            live_df = Indicators.calculate(
                df.copy()
            )

        except Exception as exc:

            return {
                "available": False,
                "reason": (
                    f"Indicator calculation failed: "
                    f"{exc}"
                ),
            }

        if live_df is None or live_df.empty:

            return {
                "available": False,
                "reason": "No usable feature data.",
            }

        # ------------------------------------------------------
        # Clean feature data
        # ------------------------------------------------------

        live_df = (
            live_df
            .replace(
                [np.inf, -np.inf],
                np.nan,
            )
            .dropna(
                subset=cls.FEATURE_COLUMNS
            )
            .reset_index(drop=True)
        )

        if live_df.empty:

            return {
                "available": False,
                "reason": (
                    "Latest candle does not have "
                    "enough indicator history."
                ),
            }

        latest = live_df.iloc[-1]

        # ------------------------------------------------------
        # Build ML input
        # ------------------------------------------------------

        X = pd.DataFrame(
            [
                [
                    latest[column]
                    for column in cls.FEATURE_COLUMNS
                ]
            ],
            columns=cls.FEATURE_COLUMNS,
        )

        # ------------------------------------------------------
        # Prediction
        # ------------------------------------------------------

        try:

            prediction = int(
                model.predict(X)[0]
            )

            probabilities = (
                model.predict_proba(X)[0]
            )

        except Exception as exc:

            return {
                "available": False,
                "reason": (
                    f"Model prediction failed: "
                    f"{exc}"
                ),
            }

        classes = [
            int(x)
            for x in model.classes_
        ]

        probs = {
            int(label): float(probability)
            for label, probability
            in zip(
                classes,
                probabilities,
            )
        }

        sell_probability = probs.get(
            0,
            0.0,
        )

        hold_probability = probs.get(
            1,
            0.0,
        )

        buy_probability = probs.get(
            2,
            0.0,
        )

        # ------------------------------------------------------
        # Signal
        # ------------------------------------------------------

        if prediction == 2:

            signal = "BUY"
            direction = "UP"
            confidence = buy_probability

        elif prediction == 0:

            signal = "SELL"
            direction = "DOWN"
            confidence = sell_probability

        else:

            signal = "HOLD"
            direction = "SIDEWAYS"
            confidence = hold_probability

        # ------------------------------------------------------
        # Latest candle OHLC
        # ------------------------------------------------------

        open_price = float(
            latest["Open"]
        )

        high = float(
            latest["High"]
        )

        low = float(
            latest["Low"]
        )

        close = float(
            latest["Close"]
        )

        atr = float(
            latest["ATR"]
        )

        # ------------------------------------------------------
        # Latest candle calculation
        # ------------------------------------------------------

        candle_body = abs(
            close - open_price
        )

        candle_range = high - low

        if candle_range > 0:

            body_percentage = (
                candle_body /
                candle_range
            ) * 100

        else:

            body_percentage = 0.0

        if close > open_price:

            latest_candle_direction = "UP"

        elif close < open_price:

            latest_candle_direction = "DOWN"

        else:

            latest_candle_direction = "NEUTRAL"

        # ------------------------------------------------------
        # Candle patterns
        # ------------------------------------------------------

        patterns = []

        pattern_columns = [

            (
                "DOJI",
                "Doji",
            ),

            (
                "HAMMER",
                "Hammer",
            ),

            (
                "INVERTED_HAMMER",
                "Inverted Hammer",
            ),

            (
                "SHOOTING_STAR",
                "Shooting Star",
            ),

            (
                "HANGING_MAN",
                "Hanging Man",
            ),

            (
                "BULLISH_ENGULFING",
                "Bullish Engulfing",
            ),

            (
                "BEARISH_ENGULFING",
                "Bearish Engulfing",
            ),

            (
                "MORNING_STAR",
                "Morning Star",
            ),

            (
                "EVENING_STAR",
                "Evening Star",
            ),
        ]

        for column, name in pattern_columns:

            if int(latest[column]) == 1:
                patterns.append(name)

        # ------------------------------------------------------
        # Indicators
        # ------------------------------------------------------

        ema20 = float(
            latest["EMA20"]
        )

        ema50 = float(
            latest["EMA50"]
        )

        ema200 = float(
            latest["EMA200"]
        )

        rsi = float(
            latest["RSI"]
        )

        macd = float(
            latest["MACD"]
        )

        macd_signal = float(
            latest["MACD_SIGNAL"]
        )

        adx = float(
            latest["ADX"]
        )

        # ------------------------------------------------------
        # Human-readable reasons
        # ------------------------------------------------------

        reasons = []

        if close > ema20 > ema50:

            reasons.append(
                "Price above EMA20 and EMA50"
            )

        elif close < ema20 < ema50:

            reasons.append(
                "Price below EMA20 and EMA50"
            )

        if macd > macd_signal:

            reasons.append(
                "MACD bullish"
            )

        elif macd < macd_signal:

            reasons.append(
                "MACD bearish"
            )

        if rsi < 30:

            reasons.append(
                "RSI oversold"
            )

        elif rsi > 70:

            reasons.append(
                "RSI overbought"
            )

        if adx >= 25:

            reasons.append(
                "Strong trend detected"
            )

        if patterns:

            reasons.append(
                "Candlestick: "
                + ", ".join(patterns)
            )

        # ------------------------------------------------------
        # Final result
        # ------------------------------------------------------

        return {

            "available": True,

            "symbol": symbol,

            "signal": signal,

            "direction": direction,

            "prediction": prediction,

            "confidence": round(
                confidence * 100,
                2,
            ),

            # ==============================================
            # ML PROBABILITIES
            # ==============================================

            "probabilities": {

                "SELL": round(
                    sell_probability * 100,
                    2,
                ),

                "HOLD": round(
                    hold_probability * 100,
                    2,
                ),

                "BUY": round(
                    buy_probability * 100,
                    2,
                ),
            },

            # ==============================================
            # CANDLE ANALYSIS
            # ==============================================

            "candle_analysis": candle_analysis,

            # ==============================================
            # LATEST CANDLE
            # ==============================================

            "latest_candle": {

                "direction": latest_candle_direction,

                "open": round(
                    open_price,
                    2,
                ),

                "high": round(
                    high,
                    2,
                ),

                "low": round(
                    low,
                    2,
                ),

                "close": round(
                    close,
                    2,
                ),

                "body": round(
                    candle_body,
                    2,
                ),

                "range": round(
                    candle_range,
                    2,
                ),

                "body_percentage": round(
                    body_percentage,
                    2,
                ),
            },

            # ==============================================
            # PRICE
            # ==============================================

            "price": round(
                close,
                2,
            ),

            "atr": round(
                atr,
                2,
            ),

            # ==============================================
            # INDICATORS
            # ==============================================

            "indicators": {

                "RSI": round(
                    rsi,
                    2,
                ),

                "EMA20": round(
                    ema20,
                    2,
                ),

                "EMA50": round(
                    ema50,
                    2,
                ),

                "EMA200": round(
                    ema200,
                    2,
                ),

                "MACD": round(
                    macd,
                    4,
                ),

                "MACD_SIGNAL": round(
                    macd_signal,
                    4,
                ),

                "ADX": round(
                    adx,
                    2,
                ),
            },

            # ==============================================
            # PATTERNS
            # ==============================================

            "candlestick_patterns": patterns,

            # ==============================================
            # REASONS
            # ==============================================

            "reasons": reasons,

            # ==============================================
            # MODEL
            # ==============================================

            "model": model_name,
            "model_source": model_source,
        }