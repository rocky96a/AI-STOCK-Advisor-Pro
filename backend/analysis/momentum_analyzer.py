import numpy as np
import pandas as pd


class MomentumAnalyzer:
    """
    Human-style momentum analysis.

    Uses:
    - RSI
    - MACD / Signal
    - MACD histogram
    - RSI slope
    - MACD slope
    - Price momentum
    - Rate of Change (ROC)
    - Recent momentum acceleration
    """

    @staticmethod
    def _empty_result(reason=None):
        result = {
            "available": False,
            "signal": "NEUTRAL",
            "strength": "WEAK",
            "bullish_score": 0.0,
            "bearish_score": 0.0,
            "rsi": 0.0,
            "rsi_state": "UNKNOWN",
            "rsi_direction": "UNKNOWN",
            "macd": 0.0,
            "macd_signal": 0.0,
            "macd_histogram": 0.0,
            "macd_state": "UNKNOWN",
            "macd_direction": "UNKNOWN",
            "roc": 0.0,
            "momentum": 0.0,
            "momentum_direction": "UNKNOWN",
            "reasons": [],
        }

        if reason:
            result["reason"] = reason

        return result

    @staticmethod
    def _direction(value, tolerance=0.001):
        if value > tolerance:
            return "UP"

        if value < -tolerance:
            return "DOWN"

        return "FLAT"

    @staticmethod
    def _strength(score):
        if score >= 75:
            return "VERY_STRONG"

        if score >= 55:
            return "STRONG"

        if score >= 35:
            return "MODERATE"

        if score >= 15:
            return "WEAK"

        return "VERY_WEAK"

    @classmethod
    def analyze(cls, df):
        """
        Analyze current momentum conditions.
        """

        if df is None or df.empty:
            return cls._empty_result(
                "No market data."
            )

        required = [
            "Close",
            "RSI",
            "MACD",
            "MACD_SIGNAL",
        ]

        missing = [
            column
            for column in required
            if column not in df.columns
        ]

        if missing:
            return cls._empty_result(
                f"Missing columns: {missing}"
            )

        work = df.copy()

        numeric_columns = [
            "Close",
            "RSI",
            "MACD",
            "MACD_SIGNAL",
        ]

        for column in numeric_columns:
            work[column] = pd.to_numeric(
                work[column],
                errors="coerce",
            )

        work = (
            work
            .replace(
                [np.inf, -np.inf],
                np.nan,
            )
            .dropna(subset=numeric_columns)
            .reset_index(drop=True)
        )

        if len(work) < 20:
            return cls._empty_result(
                "Not enough data for momentum analysis."
            )

        latest = work.iloc[-1]
        previous = work.iloc[-2]

        close = float(latest["Close"])

        rsi = float(latest["RSI"])
        previous_rsi = float(previous["RSI"])

        macd = float(latest["MACD"])
        macd_signal = float(
            latest["MACD_SIGNAL"]
        )

        previous_macd = float(
            previous["MACD"]
        )

        previous_macd_signal = float(
            previous["MACD_SIGNAL"]
        )

        # --------------------------------------------------
        # MACD histogram
        # --------------------------------------------------

        macd_histogram = (
            macd - macd_signal
        )

        previous_histogram = (
            previous_macd
            - previous_macd_signal
        )

        macd_direction = cls._direction(
            macd_histogram
            - previous_histogram
        )

        if macd_histogram > 0:
            macd_state = "BULLISH"
        elif macd_histogram < 0:
            macd_state = "BEARISH"
        else:
            macd_state = "NEUTRAL"

        # --------------------------------------------------
        # RSI state
        # --------------------------------------------------

        if rsi >= 70:
            rsi_state = "OVERBOUGHT"

        elif rsi >= 60:
            rsi_state = "BULLISH"

        elif rsi >= 50:
            rsi_state = "POSITIVE"

        elif rsi > 40:
            rsi_state = "NEGATIVE"

        elif rsi > 30:
            rsi_state = "BEARISH"

        else:
            rsi_state = "OVERSOLD"

        rsi_change = (
            rsi - previous_rsi
        )

        rsi_direction = cls._direction(
            rsi_change,
            tolerance=0.2,
        )

        # --------------------------------------------------
        # ROC
        # --------------------------------------------------

        previous_close = float(
            work.iloc[-11]["Close"]
        )

        if previous_close != 0:
            roc = (
                (close - previous_close)
                / previous_close
            ) * 100
        else:
            roc = 0.0

        momentum_direction = (
            "UP"
            if roc > 0.5
            else "DOWN"
            if roc < -0.5
            else "FLAT"
        )

        # --------------------------------------------------
        # Short momentum acceleration
        # --------------------------------------------------

        if len(work) >= 6:
            close_5 = float(
                work.iloc[-6]["Close"]
            )

            if close_5 != 0:
                short_momentum = (
                    (close - close_5)
                    / close_5
                ) * 100
            else:
                short_momentum = 0.0
        else:
            short_momentum = 0.0

        # --------------------------------------------------
        # Score
        # --------------------------------------------------

        bullish_score = 0.0
        bearish_score = 0.0

        reasons = []

        # --------------------------------------------------
        # RSI
        # --------------------------------------------------

        if 50 <= rsi < 60:
            bullish_score += 10
            reasons.append(
                "RSI above 50"
            )

        elif 60 <= rsi < 70:
            bullish_score += 15
            reasons.append(
                "RSI bullish"
            )

        elif rsi >= 70:
            bearish_score += 8
            reasons.append(
                "RSI overbought"
            )

        elif 40 < rsi < 50:
            bearish_score += 10
            reasons.append(
                "RSI below 50"
            )

        elif 30 < rsi <= 40:
            bearish_score += 15
            reasons.append(
                "RSI bearish"
            )

        elif rsi <= 30:
            bullish_score += 8
            reasons.append(
                "RSI oversold — possible reversal"
            )

        # --------------------------------------------------
        # RSI direction
        # --------------------------------------------------

        if rsi_direction == "UP":
            bullish_score += 5
            reasons.append(
                "RSI rising"
            )

        elif rsi_direction == "DOWN":
            bearish_score += 5
            reasons.append(
                "RSI falling"
            )

        # --------------------------------------------------
        # MACD
        # --------------------------------------------------

        if macd > macd_signal:
            bullish_score += 20
            reasons.append(
                "MACD above signal"
            )

        elif macd < macd_signal:
            bearish_score += 20
            reasons.append(
                "MACD below signal"
            )

        # --------------------------------------------------
        # MACD momentum
        # --------------------------------------------------

        if macd_direction == "UP":
            bullish_score += 10
            reasons.append(
                "MACD momentum improving"
            )

        elif macd_direction == "DOWN":
            bearish_score += 10
            reasons.append(
                "MACD momentum weakening"
            )

        # --------------------------------------------------
        # MACD zero line
        # --------------------------------------------------

        if macd > 0:
            bullish_score += 5
        elif macd < 0:
            bearish_score += 5

        # --------------------------------------------------
        # ROC
        # --------------------------------------------------

        if roc > 2:
            bullish_score += 15
            reasons.append(
                f"Strong positive ROC ({roc:.2f}%)"
            )

        elif roc > 0:
            bullish_score += 8
            reasons.append(
                f"Positive ROC ({roc:.2f}%)"
            )

        elif roc < -2:
            bearish_score += 15
            reasons.append(
                f"Strong negative ROC ({roc:.2f}%)"
            )

        elif roc < 0:
            bearish_score += 8
            reasons.append(
                f"Negative ROC ({roc:.2f}%)"
            )

        # --------------------------------------------------
        # Recent momentum
        # --------------------------------------------------

        if short_momentum > 1:
            bullish_score += 10
            reasons.append(
                "Strong short-term upward momentum"
            )

        elif short_momentum > 0:
            bullish_score += 5

        elif short_momentum < -1:
            bearish_score += 10
            reasons.append(
                "Strong short-term downward momentum"
            )

        elif short_momentum < 0:
            bearish_score += 5

        # --------------------------------------------------
        # Clamp scores
        # --------------------------------------------------

        bullish_score = min(
            round(bullish_score, 2),
            100.0,
        )

        bearish_score = min(
            round(bearish_score, 2),
            100.0,
        )

        difference = (
            bullish_score
            - bearish_score
        )

        if difference >= 20:
            signal = "BULLISH"

        elif difference <= -20:
            signal = "BEARISH"

        else:
            signal = "NEUTRAL"

        strength = cls._strength(
            abs(difference)
        )

        return {
            "available": True,

            "signal": signal,

            "strength": strength,

            "bullish_score": bullish_score,

            "bearish_score": bearish_score,

            "rsi": round(rsi, 2),

            "rsi_state": rsi_state,

            "rsi_direction": rsi_direction,

            "macd": round(macd, 4),

            "macd_signal": round(
                macd_signal,
                4,
            ),

            "macd_histogram": round(
                macd_histogram,
                4,
            ),

            "macd_state": macd_state,

            "macd_direction": macd_direction,

            "roc": round(roc, 2),

            "momentum": round(
                short_momentum,
                2,
            ),

            "momentum_direction": momentum_direction,

            "reasons": reasons,
        }