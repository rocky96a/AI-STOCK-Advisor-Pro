import numpy as np
import pandas as pd


class VolumeAnalyzer:
    """
    Human-style volume analysis.

    Analyzes:
    - Volume vs average volume
    - Volume spikes
    - Volume trend
    - Price/volume confirmation
    - OBV
    - Buying/selling pressure
    """

    @staticmethod
    def _empty_result(reason=None):
        result = {
            "available": False,

            "signal": "NEUTRAL",
            "strength": "WEAK",

            "bullish_score": 0.0,
            "bearish_score": 0.0,

            "volume": 0.0,
            "average_volume": 0.0,
            "volume_ratio": 0.0,

            "volume_state": "UNKNOWN",
            "volume_direction": "UNKNOWN",

            "price_direction": "UNKNOWN",
            "confirmation": "UNKNOWN",

            "obv": 0.0,
            "obv_direction": "UNKNOWN",

            "volume_spike": False,

            "reasons": [],
        }

        if reason:
            result["reason"] = reason

        return result

    @staticmethod
    def _direction(value, tolerance=0.01):
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
        Complete volume analysis.
        """

        if df is None or df.empty:
            return cls._empty_result(
                "No market data."
            )

        required = [
            "Open",
            "Close",
            "Volume",
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

        for column in required:
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
            .dropna(subset=required)
            .reset_index(drop=True)
        )

        if len(work) < 20:
            return cls._empty_result(
                "Not enough data for volume analysis."
            )

        # --------------------------------------------------
        # Current volume
        # --------------------------------------------------

        latest = work.iloc[-1]
        previous = work.iloc[-2]

        volume = float(
            latest["Volume"]
        )

        previous_volume = float(
            previous["Volume"]
        )

        # 20-period average
        average_volume = float(
            work["Volume"]
            .tail(20)
            .mean()
        )

        if average_volume > 0:
            volume_ratio = (
                volume / average_volume
            )
        else:
            volume_ratio = 0.0

        # --------------------------------------------------
        # Volume state
        # --------------------------------------------------

        if volume_ratio >= 2.0:
            volume_state = "EXTREME_SPIKE"

        elif volume_ratio >= 1.5:
            volume_state = "HIGH"

        elif volume_ratio >= 1.1:
            volume_state = "ABOVE_AVERAGE"

        elif volume_ratio >= 0.8:
            volume_state = "NORMAL"

        else:
            volume_state = "LOW"

        # --------------------------------------------------
        # Volume direction
        # --------------------------------------------------

        if previous_volume > 0:
            volume_change = (
                volume
                - previous_volume
            ) / previous_volume
        else:
            volume_change = 0.0

        volume_direction = cls._direction(
            volume_change
        )

        # --------------------------------------------------
        # Price direction
        # --------------------------------------------------

        open_price = float(
            latest["Open"]
        )

        close = float(
            latest["Close"]
        )

        if close > open_price:
            price_direction = "UP"

        elif close < open_price:
            price_direction = "DOWN"

        else:
            price_direction = "NEUTRAL"

        # --------------------------------------------------
        # OBV
        # --------------------------------------------------

        obv = 0.0

        obv_values = []

        previous_close = None

        for _, row in work.iterrows():

            current_close = float(
                row["Close"]
            )

            current_volume = float(
                row["Volume"]
            )

            if previous_close is None:
                pass

            elif current_close > previous_close:
                obv += current_volume

            elif current_close < previous_close:
                obv -= current_volume

            obv_values.append(obv)

            previous_close = current_close

        work["OBV_CALCULATED"] = obv_values

        current_obv = float(
            work.iloc[-1]["OBV_CALCULATED"]
        )

        previous_obv = float(
            work.iloc[-6]["OBV_CALCULATED"]
        )

        obv_change = (
            current_obv
            - previous_obv
        )

        if obv_change > 0:
            obv_direction = "UP"

        elif obv_change < 0:
            obv_direction = "DOWN"

        else:
            obv_direction = "FLAT"

        # --------------------------------------------------
        # Price/volume confirmation
        # --------------------------------------------------

        if (
            price_direction == "UP"
            and volume_ratio >= 1.1
        ):
            confirmation = "BULLISH_CONFIRMED"

        elif (
            price_direction == "DOWN"
            and volume_ratio >= 1.1
        ):
            confirmation = "BEARISH_CONFIRMED"

        elif (
            price_direction == "UP"
            and volume_ratio < 0.8
        ):
            confirmation = "WEAK_BULLISH_MOVE"

        elif (
            price_direction == "DOWN"
            and volume_ratio < 0.8
        ):
            confirmation = "WEAK_BEARISH_MOVE"

        else:
            confirmation = "NEUTRAL"

        volume_spike = volume_ratio >= 1.5

        # --------------------------------------------------
        # Score
        # --------------------------------------------------

        bullish_score = 0.0
        bearish_score = 0.0

        reasons = []

        # --------------------------------------------------
        # Price + volume
        # --------------------------------------------------

        if (
            price_direction == "UP"
            and volume_ratio >= 1.5
        ):
            bullish_score += 30
            reasons.append(
                "Strong bullish price move with high volume"
            )

        elif (
            price_direction == "UP"
            and volume_ratio >= 1.1
        ):
            bullish_score += 20
            reasons.append(
                "Price rise confirmed by volume"
            )

        elif (
            price_direction == "UP"
            and volume_ratio < 0.8
        ):
            bearish_score += 5
            reasons.append(
                "Price rising on weak volume"
            )

        # --------------------------------------------------
        # Bearish price + volume
        # --------------------------------------------------

        if (
            price_direction == "DOWN"
            and volume_ratio >= 1.5
        ):
            bearish_score += 30
            reasons.append(
                "Strong bearish price move with high volume"
            )

        elif (
            price_direction == "DOWN"
            and volume_ratio >= 1.1
        ):
            bearish_score += 20
            reasons.append(
                "Price fall confirmed by volume"
            )

        elif (
            price_direction == "DOWN"
            and volume_ratio < 0.8
        ):
            bullish_score += 5
            reasons.append(
                "Price falling on weak volume"
            )

        # --------------------------------------------------
        # OBV
        # --------------------------------------------------

        if obv_direction == "UP":
            bullish_score += 15
            reasons.append(
                "OBV rising — accumulation pressure"
            )

        elif obv_direction == "DOWN":
            bearish_score += 15
            reasons.append(
                "OBV falling — distribution pressure"
            )

        # --------------------------------------------------
        # Volume spike
        # --------------------------------------------------

        if volume_ratio >= 2.0:

            if price_direction == "UP":
                bullish_score += 15
                reasons.append(
                    "Extreme volume spike on bullish candle"
                )

            elif price_direction == "DOWN":
                bearish_score += 15
                reasons.append(
                    "Extreme volume spike on bearish candle"
                )

        # --------------------------------------------------
        # Volume trend
        # --------------------------------------------------

        if volume_direction == "UP":

            if price_direction == "UP":
                bullish_score += 10

            elif price_direction == "DOWN":
                bearish_score += 10

        # --------------------------------------------------
        # Clamp
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

            "volume": round(
                volume,
                2,
            ),

            "average_volume": round(
                average_volume,
                2,
            ),

            "volume_ratio": round(
                volume_ratio,
                2,
            ),

            "volume_state": volume_state,

            "volume_direction": volume_direction,

            "price_direction": price_direction,

            "confirmation": confirmation,

            "obv": round(
                current_obv,
                2,
            ),

            "obv_direction": obv_direction,

            "volume_spike": volume_spike,

            "reasons": reasons,
        }