"""
Human-style candlestick analysis.

This module analyzes:
- candle direction
- body strength
- wick pressure
- close location
- consecutive up/down candles
- common candlestick patterns
- bullish/bearish pressure

It does NOT predict the future by itself.
It produces technical evidence for the final analysis engine.
"""

import numpy as np
import pandas as pd


class CandleAnalyzer:

    @staticmethod
    def analyze(df, lookback=20):
        """
        Analyze the latest candle and recent candle behavior.

        Parameters
        ----------
        df : pandas.DataFrame
            OHLCV dataframe.

        lookback : int
            Number of recent candles used for pressure analysis.

        Returns
        -------
        dict
        """

        empty_result = {
            "available": False,
            "total_candles": 0,
            "current_direction": "NEUTRAL",
            "current_up_streak": 0,
            "current_down_streak": 0,
            "up_candles": 0,
            "down_candles": 0,
            "neutral_candles": 0,
            "up_percentage": 0.0,
            "down_percentage": 0.0,
            "neutral_percentage": 0.0,
            "bullish_score": 0.0,
            "bearish_score": 0.0,
            "signal": "NEUTRAL",
            "strength": "WEAK",
            "patterns": [],
            "reasons": [],
            "recent_candles": [],
        }

        if df is None or df.empty:
            return empty_result

        required = [
            "Open",
            "High",
            "Low",
            "Close",
        ]

        missing = [
            column
            for column in required
            if column not in df.columns
        ]

        if missing:
            result = empty_result.copy()
            result["reason"] = (
                f"Missing columns: {missing}"
            )
            return result

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
            .dropna(
                subset=required
            )
            .reset_index(drop=True)
        )

        if work.empty:
            return empty_result

        # --------------------------------------------------
        # Basic candle calculations
        # --------------------------------------------------

        work["BODY"] = (
            work["Close"] - work["Open"]
        )

        work["BODY_SIZE"] = (
            work["BODY"].abs()
        )

        work["RANGE"] = (
            work["High"] - work["Low"]
        )

        work["UPPER_WICK"] = (
            work["High"]
            - work[["Open", "Close"]].max(axis=1)
        )

        work["LOWER_WICK"] = (
            work[["Open", "Close"]].min(axis=1)
            - work["Low"]
        )

        work["BODY_RATIO"] = np.where(
            work["RANGE"] > 0,
            work["BODY_SIZE"]
            / work["RANGE"],
            0.0,
        )

        work["UPPER_WICK_RATIO"] = np.where(
            work["RANGE"] > 0,
            work["UPPER_WICK"]
            / work["RANGE"],
            0.0,
        )

        work["LOWER_WICK_RATIO"] = np.where(
            work["RANGE"] > 0,
            work["LOWER_WICK"]
            / work["RANGE"],
            0.0,
        )

        # --------------------------------------------------
        # Direction
        # --------------------------------------------------

        work["DIRECTION"] = np.where(
            work["Close"] > work["Open"],
            "UP",
            np.where(
                work["Close"] < work["Open"],
                "DOWN",
                "NEUTRAL",
            ),
        )

        total = len(work)

        up_count = int(
            (work["DIRECTION"] == "UP").sum()
        )

        down_count = int(
            (work["DIRECTION"] == "DOWN").sum()
        )

        neutral_count = int(
            (work["DIRECTION"] == "NEUTRAL").sum()
        )

        # --------------------------------------------------
        # Current streak
        # --------------------------------------------------

        directions = work["DIRECTION"].tolist()

        current_up_streak = 0
        current_down_streak = 0

        for direction in reversed(directions):

            if direction == "UP":
                current_up_streak += 1
            else:
                break

        for direction in reversed(directions):

            if direction == "DOWN":
                current_down_streak += 1
            else:
                break

        # --------------------------------------------------
        # Latest candle
        # --------------------------------------------------

        latest = work.iloc[-1]

        open_price = float(latest["Open"])
        high = float(latest["High"])
        low = float(latest["Low"])
        close = float(latest["Close"])

        body = float(latest["BODY_SIZE"])
        candle_range = float(latest["RANGE"])

        upper_wick = float(
            latest["UPPER_WICK"]
        )

        lower_wick = float(
            latest["LOWER_WICK"]
        )

        body_ratio = float(
            latest["BODY_RATIO"]
        )

        upper_wick_ratio = float(
            latest["UPPER_WICK_RATIO"]
        )

        lower_wick_ratio = float(
            latest["LOWER_WICK_RATIO"]
        )

        current_direction = (
            str(latest["DIRECTION"])
        )

        # --------------------------------------------------
        # Close location
        #
        # 0 = close at low
        # 1 = close at high
        # --------------------------------------------------

        if candle_range > 0:

            close_location = (
                (close - low)
                / candle_range
            )

        else:

            close_location = 0.5

        # --------------------------------------------------
        # Candle strength
        # --------------------------------------------------

        if body_ratio >= 0.70:
            strength = "VERY_STRONG"

        elif body_ratio >= 0.55:
            strength = "STRONG"

        elif body_ratio >= 0.30:
            strength = "MODERATE"

        else:
            strength = "WEAK"

        # --------------------------------------------------
        # Scores
        # --------------------------------------------------

        bullish_score = 0.0
        bearish_score = 0.0

        reasons = []

        # Direction
        if current_direction == "UP":
            bullish_score += 20

        elif current_direction == "DOWN":
            bearish_score += 20

        # Strong body
        if body_ratio >= 0.70:

            if current_direction == "UP":
                bullish_score += 25
                reasons.append(
                    "Strong bullish candle body"
                )

            elif current_direction == "DOWN":
                bearish_score += 25
                reasons.append(
                    "Strong bearish candle body"
                )

        elif body_ratio >= 0.55:

            if current_direction == "UP":
                bullish_score += 15

            elif current_direction == "DOWN":
                bearish_score += 15

        # Close near high
        if close_location >= 0.80:

            bullish_score += 15

            reasons.append(
                "Candle closed near its high"
            )

        # Close near low
        elif close_location <= 0.20:

            bearish_score += 15

            reasons.append(
                "Candle closed near its low"
            )

        # --------------------------------------------------
        # Wick analysis
        # --------------------------------------------------

        if (
            lower_wick_ratio >= 0.40
            and lower_wick > body
        ):

            bullish_score += 15

            reasons.append(
                "Strong lower-wick rejection"
            )

        if (
            upper_wick_ratio >= 0.40
            and upper_wick > body
        ):

            bearish_score += 15

            reasons.append(
                "Strong upper-wick rejection"
            )

        # --------------------------------------------------
        # Candlestick patterns
        # --------------------------------------------------

        patterns = []

        patterns.extend(
            CandleAnalyzer._detect_single_patterns(
                work
            )
        )

        patterns.extend(
            CandleAnalyzer._detect_multi_patterns(
                work
            )
        )

        # Remove duplicates while preserving order
        patterns = list(
            dict.fromkeys(patterns)
        )

        # Pattern scoring
        for pattern in patterns:

            if pattern in {
                "Hammer",
                "Inverted Hammer",
                "Bullish Engulfing",
                "Morning Star",
                "Bullish Harami",
            }:

                bullish_score += 15

            elif pattern in {
                "Shooting Star",
                "Hanging Man",
                "Bearish Engulfing",
                "Evening Star",
                "Bearish Harami",
            }:

                bearish_score += 15

        if patterns:

            reasons.append(
                "Patterns: "
                + ", ".join(patterns)
            )

        # --------------------------------------------------
        # Recent candle pressure
        # --------------------------------------------------

        recent = work.tail(
            max(1, lookback)
        )

        recent_total = len(recent)

        recent_up = int(
            (
                recent["DIRECTION"] == "UP"
            ).sum()
        )

        recent_down = int(
            (
                recent["DIRECTION"] == "DOWN"
            ).sum()
        )

        if recent_total > 0:

            recent_up_pct = (
                recent_up
                / recent_total
                * 100
            )

            recent_down_pct = (
                recent_down
                / recent_total
                * 100
            )

        else:

            recent_up_pct = 0.0
            recent_down_pct = 0.0

        if recent_up_pct >= 60:

            bullish_score += 15

            reasons.append(
                f"Recent candles show "
                f"{recent_up_pct:.1f}% bullish closes"
            )

        elif recent_down_pct >= 60:

            bearish_score += 15

            reasons.append(
                f"Recent candles show "
                f"{recent_down_pct:.1f}% bearish closes"
            )

        # --------------------------------------------------
        # Consecutive candles
        # --------------------------------------------------

        if current_up_streak >= 3:

            bullish_score += 10

            reasons.append(
                f"{current_up_streak} consecutive "
                f"up candles"
            )

        if current_down_streak >= 3:

            bearish_score += 10

            reasons.append(
                f"{current_down_streak} consecutive "
                f"down candles"
            )

        # --------------------------------------------------
        # Cap scores
        # --------------------------------------------------

        bullish_score = min(
            bullish_score,
            100.0,
        )

        bearish_score = min(
            bearish_score,
            100.0,
        )

        # --------------------------------------------------
        # Final candle signal
        # --------------------------------------------------

        difference = (
            bullish_score
            - bearish_score
        )

        if difference >= 15:

            signal = "BULLISH"

        elif difference <= -15:

            signal = "BEARISH"

        else:

            signal = "NEUTRAL"

        # --------------------------------------------------
        # Recent candle display
        # --------------------------------------------------

        recent_candles = []

        for _, row in work.tail(10).iterrows():

            if row["DIRECTION"] == "UP":
                symbol = "↑"

            elif row["DIRECTION"] == "DOWN":
                symbol = "↓"

            else:
                symbol = "→"

            recent_candles.append(
                {
                    "direction": str(
                        row["DIRECTION"]
                    ),
                    "symbol": symbol,
                    "open": round(
                        float(row["Open"]),
                        2,
                    ),
                    "close": round(
                        float(row["Close"]),
                        2,
                    ),
                }
            )

        return {
            "available": True,

            "total_candles": total,

            "current_direction":
                current_direction,

            "current_up_streak":
                current_up_streak,

            "current_down_streak":
                current_down_streak,

            "up_candles":
                up_count,

            "down_candles":
                down_count,

            "neutral_candles":
                neutral_count,

            "up_percentage": round(
                up_count / total * 100,
                2,
            ),

            "down_percentage": round(
                down_count / total * 100,
                2,
            ),

            "neutral_percentage": round(
                neutral_count / total * 100,
                2,
            ),

            "recent_up_percentage":
                round(
                    recent_up_pct,
                    2,
                ),

            "recent_down_percentage":
                round(
                    recent_down_pct,
                    2,
                ),

            "latest_candle": {
                "direction":
                    current_direction,

                "open":
                    round(open_price, 2),

                "high":
                    round(high, 2),

                "low":
                    round(low, 2),

                "close":
                    round(close, 2),

                "body":
                    round(body, 2),

                "range":
                    round(candle_range, 2),

                "body_percentage":
                    round(
                        body_ratio * 100,
                        2,
                    ),

                "upper_wick":
                    round(
                        upper_wick,
                        2,
                    ),

                "lower_wick":
                    round(
                        lower_wick,
                        2,
                    ),

                "upper_wick_percentage":
                    round(
                        upper_wick_ratio * 100,
                        2,
                    ),

                "lower_wick_percentage":
                    round(
                        lower_wick_ratio * 100,
                        2,
                    ),

                "close_location":
                    round(
                        close_location * 100,
                        2,
                    ),
            },

            "patterns": patterns,

            "bullish_score": round(
                bullish_score,
                2,
            ),

            "bearish_score": round(
                bearish_score,
                2,
            ),

            "signal": signal,

            "strength": strength,

            "reasons": reasons,

            "recent_candles":
                recent_candles,
        }

    # ==================================================
    # Single candle patterns
    # ==================================================

    @staticmethod
    def _detect_single_patterns(df):

        patterns = []

        if df.empty:
            return patterns

        row = df.iloc[-1]

        body = float(row["BODY_SIZE"])
        candle_range = float(row["RANGE"])
        upper = float(row["UPPER_WICK"])
        lower = float(row["LOWER_WICK"])

        if candle_range <= 0:
            return patterns

        body_ratio = (
            body / candle_range
        )

        upper_ratio = (
            upper / candle_range
        )

        lower_ratio = (
            lower / candle_range
        )

        # Doji
        if body_ratio <= 0.10:

            patterns.append("Doji")

        # Hammer
        if (
            lower_ratio >= 0.50
            and upper_ratio <= 0.20
            and body_ratio <= 0.40
        ):

            patterns.append("Hammer")

        # Inverted hammer
        if (
            upper_ratio >= 0.50
            and lower_ratio <= 0.20
            and body_ratio <= 0.40
        ):

            patterns.append(
                "Inverted Hammer"
            )

        # Shooting star
        if (
            upper_ratio >= 0.50
            and lower_ratio <= 0.20
            and body_ratio <= 0.40
            and row["DIRECTION"] == "DOWN"
        ):

            patterns.append(
                "Shooting Star"
            )

        # Hanging man
        if (
            lower_ratio >= 0.50
            and upper_ratio <= 0.20
            and body_ratio <= 0.40
            and row["DIRECTION"] == "DOWN"
        ):

            patterns.append(
                "Hanging Man"
            )

        return patterns

    # ==================================================
    # Two / three candle patterns
    # ==================================================

    @staticmethod
    def _detect_multi_patterns(df):

        patterns = []

        if len(df) < 2:
            return patterns

        previous = df.iloc[-2]
        current = df.iloc[-1]

        prev_open = float(
            previous["Open"]
        )

        prev_close = float(
            previous["Close"]
        )

        curr_open = float(
            current["Open"]
        )

        curr_close = float(
            current["Close"]
        )

        # --------------------------------------------------
        # Bullish engulfing
        # --------------------------------------------------

        if (
            prev_close < prev_open
            and curr_close > curr_open
            and curr_open <= prev_close
            and curr_close >= prev_open
        ):

            patterns.append(
                "Bullish Engulfing"
            )

        # --------------------------------------------------
        # Bearish engulfing
        # --------------------------------------------------

        if (
            prev_close > prev_open
            and curr_close < curr_open
            and curr_open >= prev_close
            and curr_close <= prev_open
        ):

            patterns.append(
                "Bearish Engulfing"
            )

        # --------------------------------------------------
        # Harami
        # --------------------------------------------------

        prev_high_body = max(
            prev_open,
            prev_close,
        )

        prev_low_body = min(
            prev_open,
            prev_close,
        )

        curr_high_body = max(
            curr_open,
            curr_close,
        )

        curr_low_body = min(
            curr_open,
            curr_close,
        )

        if (
            prev_close < prev_open
            and curr_high_body <= prev_high_body
            and curr_low_body >= prev_low_body
            and curr_close > curr_open
        ):

            patterns.append(
                "Bullish Harami"
            )

        if (
            prev_close > prev_open
            and curr_high_body <= prev_high_body
            and curr_low_body >= prev_low_body
            and curr_close < curr_open
        ):

            patterns.append(
                "Bearish Harami"
            )

        # --------------------------------------------------
        # Three candle patterns
        # --------------------------------------------------

        if len(df) >= 3:

            first = df.iloc[-3]
            second = df.iloc[-2]
            third = df.iloc[-1]

            first_open = float(
                first["Open"]
            )

            first_close = float(
                first["Close"]
            )

            second_open = float(
                second["Open"]
            )

            second_close = float(
                second["Close"]
            )

            third_open = float(
                third["Open"]
            )

            third_close = float(
                third["Close"]
            )

            first_body = abs(
                first_close - first_open
            )

            second_body = abs(
                second_close - second_open
            )

            third_body = abs(
                third_close - third_open
            )

            # Morning Star
            if (
                first_close < first_open
                and second_body
                < first_body * 0.5
                and third_close > third_open
                and third_close
                > (
                    first_open
                    + first_close
                ) / 2
            ):

                patterns.append(
                    "Morning Star"
                )

            # Evening Star
            if (
                first_close > first_open
                and second_body
                < first_body * 0.5
                and third_close < third_open
                and third_close
                < (
                    first_open
                    + first_close
                ) / 2
            ):

                patterns.append(
                    "Evening Star"
                )

        return patterns