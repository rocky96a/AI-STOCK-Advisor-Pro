import numpy as np
import pandas as pd


class SupportResistanceAnalyzer:

    @staticmethod
    def analyze(df, lookback=100):

        if df is None or df.empty:
            return {
                "available": False,
                "reason": "No market data.",
            }

        required = ["High", "Low", "Close"]

        missing = [
            col
            for col in required
            if col not in df.columns
        ]

        if missing:
            return {
                "available": False,
                "reason": f"Missing columns: {missing}",
            }

        work = df.copy()

        for col in required:
            work[col] = pd.to_numeric(
                work[col],
                errors="coerce",
            )

        work = (
            work
            .dropna(subset=required)
            .reset_index(drop=True)
        )

        if len(work) < 20:
            return {
                "available": False,
                "reason": "Not enough candles.",
            }

        work = work.tail(
            min(lookback, len(work))
        ).reset_index(drop=True)

        close = float(
            work["Close"].iloc[-1]
        )

        highs = work["High"].values
        lows = work["Low"].values

        # --------------------------------------------------
        # Detect swing points
        # --------------------------------------------------

        swing_highs = []
        swing_lows = []

        for i in range(2, len(work) - 2):

            high = highs[i]
            low = lows[i]

            surrounding_highs = [
                highs[i - 2],
                highs[i - 1],
                highs[i + 1],
                highs[i + 2],
            ]

            surrounding_lows = [
                lows[i - 2],
                lows[i - 1],
                lows[i + 1],
                lows[i + 2],
            ]

            if high >= max(surrounding_highs):
                swing_highs.append(
                    float(high)
                )

            if low <= min(surrounding_lows):
                swing_lows.append(
                    float(low)
                )

        # --------------------------------------------------
        # Add major rolling levels
        # --------------------------------------------------

        rolling_high = float(
            work["High"].max()
        )

        rolling_low = float(
            work["Low"].min()
        )

        swing_highs.append(
            rolling_high
        )

        swing_lows.append(
            rolling_low
        )

        # --------------------------------------------------
        # Cluster nearby levels
        # --------------------------------------------------

        def cluster_levels(
            levels,
            tolerance=0.015,
        ):

            if not levels:
                return []

            levels = sorted(levels)

            clusters = []

            current = [levels[0]]

            for level in levels[1:]:

                average = np.mean(current)

                if (
                    abs(level - average)
                    / average
                    <= tolerance
                ):
                    current.append(level)

                else:
                    clusters.append(current)
                    current = [level]

            clusters.append(current)

            result = []

            for cluster in clusters:

                result.append({
                    "price": round(
                        float(np.mean(cluster)),
                        2,
                    ),
                    "touches": len(cluster),
                })

            return result

        supports = cluster_levels(
            [
                level
                for level in swing_lows
                if level < close
            ]
        )

        resistances = cluster_levels(
            [
                level
                for level in swing_highs
                if level > close
            ]
        )

        # --------------------------------------------------
        # Nearest support
        # --------------------------------------------------

        nearest_support = None

        if supports:
            nearest_support = max(
                supports,
                key=lambda x: x["price"],
            )

        # --------------------------------------------------
        # Nearest resistance
        # --------------------------------------------------

        nearest_resistance = None

        if resistances:
            nearest_resistance = min(
                resistances,
                key=lambda x: x["price"],
            )

        # --------------------------------------------------
        # Distances
        # --------------------------------------------------

        support_distance = None
        resistance_distance = None

        if nearest_support:

            support_distance = (
                (
                    close
                    - nearest_support["price"]
                )
                / close
            ) * 100

        if nearest_resistance:

            resistance_distance = (
                (
                    nearest_resistance["price"]
                    - close
                )
                / close
            ) * 100

        # --------------------------------------------------
        # Breakout / breakdown detection
        # --------------------------------------------------

        previous_close = float(
            work["Close"].iloc[-2]
        )

        breakout = False
        breakdown = False

        if nearest_resistance:

            resistance_price = (
                nearest_resistance["price"]
            )

            if (
                close > resistance_price
                and previous_close
                <= resistance_price
            ):
                breakout = True

        if nearest_support:

            support_price = (
                nearest_support["price"]
            )

            if (
                close < support_price
                and previous_close
                >= support_price
            ):
                breakdown = True

        # --------------------------------------------------
        # Score
        # --------------------------------------------------

        bullish_score = 0.0
        bearish_score = 0.0

        reasons = []

        if breakout:

            bullish_score += 40

            reasons.append(
                "Resistance breakout detected"
            )

        if breakdown:

            bearish_score += 40

            reasons.append(
                "Support breakdown detected"
            )

        # Price close to support can create
        # bullish reaction potential.

        if (
            support_distance is not None
            and support_distance <= 3
        ):

            bullish_score += 15

            reasons.append(
                "Price near support"
            )

        # Price close to resistance creates
        # rejection risk.

        if (
            resistance_distance is not None
            and resistance_distance <= 3
        ):

            bearish_score += 15

            reasons.append(
                "Price near resistance"
            )

        # --------------------------------------------------
        # Signal
        # --------------------------------------------------

        if bullish_score >= bearish_score + 20:

            signal = "BULLISH"

        elif bearish_score >= bullish_score + 20:

            signal = "BEARISH"

        else:

            signal = "NEUTRAL"

        difference = abs(
            bullish_score - bearish_score
        )

        if difference >= 40:

            strength = "STRONG"

        elif difference >= 20:

            strength = "MODERATE"

        else:

            strength = "WEAK"

        return {

            "available": True,

            "signal": signal,

            "strength": strength,

            "bullish_score": round(
                bullish_score,
                2,
            ),

            "bearish_score": round(
                bearish_score,
                2,
            ),

            "current_price": round(
                close,
                2,
            ),

            "nearest_support": (
                nearest_support
            ),

            "nearest_resistance": (
                nearest_resistance
            ),

            "support_distance_percentage": (
                round(
                    support_distance,
                    2,
                )
                if support_distance is not None
                else None
            ),

            "resistance_distance_percentage": (
                round(
                    resistance_distance,
                    2,
                )
                if resistance_distance is not None
                else None
            ),

            "support_levels": supports,

            "resistance_levels": resistances,

            "breakout": breakout,

            "breakdown": breakdown,

            "reasons": reasons,
        }