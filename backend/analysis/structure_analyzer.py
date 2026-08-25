import numpy as np
import pandas as pd


class StructureAnalyzer:

    @staticmethod
    def analyze(df, lookback=50):
        """
        Analyze market structure using:
        - Higher Highs (HH)
        - Higher Lows (HL)
        - Lower Highs (LH)
        - Lower Lows (LL)
        - Swing structure
        - Recent price position
        """

        if df is None or df.empty:
            return {
                "available": False,
                "reason": "No market data.",
            }

        required = ["High", "Low", "Close"]

        missing = [
            col for col in required
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

        if len(work) < 10:
            return {
                "available": False,
                "reason": "Not enough candles.",
            }

        work = work.tail(lookback).reset_index(drop=True)

        highs = work["High"].values
        lows = work["Low"].values
        close = float(work["Close"].iloc[-1])

        # --------------------------------------------------
        # Find simple swing highs/lows
        # --------------------------------------------------

        swing_highs = []
        swing_lows = []

        for i in range(1, len(work) - 1):

            if (
                highs[i] > highs[i - 1]
                and highs[i] >= highs[i + 1]
            ):
                swing_highs.append(
                    (i, float(highs[i]))
                )

            if (
                lows[i] < lows[i - 1]
                and lows[i] <= lows[i + 1]
            ):
                swing_lows.append(
                    (i, float(lows[i]))
                )

        # Keep recent swings.
        recent_highs = swing_highs[-5:]
        recent_lows = swing_lows[-5:]

        higher_highs = 0
        lower_highs = 0
        higher_lows = 0
        lower_lows = 0

        # --------------------------------------------------
        # Compare swing highs
        # --------------------------------------------------

        for i in range(1, len(recent_highs)):

            previous = recent_highs[i - 1][1]
            current = recent_highs[i][1]

            if current > previous:
                higher_highs += 1

            elif current < previous:
                lower_highs += 1

        # --------------------------------------------------
        # Compare swing lows
        # --------------------------------------------------

        for i in range(1, len(recent_lows)):

            previous = recent_lows[i - 1][1]
            current = recent_lows[i][1]

            if current > previous:
                higher_lows += 1

            elif current < previous:
                lower_lows += 1

        bullish_score = 0.0
        bearish_score = 0.0
        reasons = []

        # --------------------------------------------------
        # Structure interpretation
        # --------------------------------------------------

        if higher_highs >= 2:
            bullish_score += 20
            reasons.append(
                "Higher High structure detected"
            )

        if higher_lows >= 2:
            bullish_score += 20
            reasons.append(
                "Higher Low structure detected"
            )

        if lower_highs >= 2:
            bearish_score += 20
            reasons.append(
                "Lower High structure detected"
            )

        if lower_lows >= 2:
            bearish_score += 20
            reasons.append(
                "Lower Low structure detected"
            )

        # --------------------------------------------------
        # Determine structure
        # --------------------------------------------------

        if (
            higher_highs >= 2
            and higher_lows >= 2
        ):
            structure = "BULLISH"

        elif (
            lower_highs >= 2
            and lower_lows >= 2
        ):
            structure = "BEARISH"

        elif bullish_score > bearish_score:
            structure = "BULLISH"

        elif bearish_score > bullish_score:
            structure = "BEARISH"

        else:
            structure = "SIDEWAYS"

        # --------------------------------------------------
        # Recent swing levels
        # --------------------------------------------------

        resistance = None
        support = None

        if recent_highs:
            resistance = max(
                value
                for _, value in recent_highs
            )

        if recent_lows:
            support = min(
                value
                for _, value in recent_lows
            )

        # --------------------------------------------------
        # Distance from levels
        # --------------------------------------------------

        resistance_distance = None
        support_distance = None

        if resistance is not None:
            resistance_distance = (
                (resistance - close)
                / close
            ) * 100

        if support is not None:
            support_distance = (
                (close - support)
                / close
            ) * 100

        # --------------------------------------------------
        # Structure signal
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

            "structure": structure,

            "strength": strength,

            "bullish_score": round(
                bullish_score,
                2,
            ),

            "bearish_score": round(
                bearish_score,
                2,
            ),

            "close": round(
                close,
                2,
            ),

            "higher_highs": higher_highs,

            "lower_highs": lower_highs,

            "higher_lows": higher_lows,

            "lower_lows": lower_lows,

            "support": (
                round(support, 2)
                if support is not None
                else None
            ),

            "resistance": (
                round(resistance, 2)
                if resistance is not None
                else None
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

            "recent_swing_highs": [
                round(value, 2)
                for _, value in recent_highs
            ],

            "recent_swing_lows": [
                round(value, 2)
                for _, value in recent_lows
            ],

            "reasons": reasons,
        }