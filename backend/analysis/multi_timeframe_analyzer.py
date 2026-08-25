import numpy as np
import pandas as pd

from backend.features.indicators import Indicators
from backend.analysis.trend_analyzer import TrendAnalyzer
from backend.analysis.momentum_analyzer import MomentumAnalyzer
from backend.analysis.candle_analyzer import CandleAnalyzer
from backend.analysis.volume_analyzer import VolumeAnalyzer
from backend.analysis.structure_analyzer import StructureAnalyzer
from backend.analysis.support_resistance_analyzer import (
    SupportResistanceAnalyzer,
)


class MultiTimeframeAnalyzer:

    TIMEFRAME_ORDER = [
        "1d",
        "1h",
        "15m",
    ]

    TIMEFRAME_NAMES = {
        "1d": "DAILY",
        "1h": "HOURLY",
        "15m": "INTRADAY",
    }

    # ======================================================
    # EMPTY RESULT
    # ======================================================

    @staticmethod
    def _unavailable(reason="No data"):

        return {
            "available": False,
            "signal": "UNAVAILABLE",
            "direction": "UNKNOWN",
            "strength": "NONE",
            "reason": reason,
        }

    # ======================================================
    # ANALYZE ONE TIMEFRAME
    # ======================================================

    @staticmethod
    def _analyze_timeframe(df, interval):

        if df is None or df.empty:

            return MultiTimeframeAnalyzer._unavailable(
                "No timeframe data"
            )

        work = df.copy()

        try:

            work = Indicators.calculate(work)

        except Exception as exc:

            return MultiTimeframeAnalyzer._unavailable(
                f"Indicator calculation failed: {exc}"
            )

        if work is None or work.empty:

            return MultiTimeframeAnalyzer._unavailable(
                "No usable indicator data"
            )

        results = {}

        # --------------------------------------------------
        # Trend
        # --------------------------------------------------

        try:

            results["trend"] = (
                TrendAnalyzer.analyze(work)
            )

        except Exception:

            results["trend"] = {
                "available": False,
                "signal": "NEUTRAL",
                "strength": "WEAK",
            }

        # --------------------------------------------------
        # Momentum
        # --------------------------------------------------

        try:

            results["momentum"] = (
                MomentumAnalyzer.analyze(work)
            )

        except Exception:

            results["momentum"] = {
                "available": False,
                "signal": "NEUTRAL",
                "strength": "WEAK",
            }

        # --------------------------------------------------
        # Candle
        # --------------------------------------------------

        try:

            results["candle"] = (
                CandleAnalyzer.analyze(work)
            )

        except Exception:

            results["candle"] = {
                "available": False,
                "signal": "NEUTRAL",
                "strength": "WEAK",
            }

        # --------------------------------------------------
        # Volume
        # --------------------------------------------------

        try:

            results["volume"] = (
                VolumeAnalyzer.analyze(work)
            )

        except Exception:

            results["volume"] = {
                "available": False,
                "signal": "NEUTRAL",
                "strength": "WEAK",
            }

        # --------------------------------------------------
        # Structure
        # --------------------------------------------------

        try:

            results["structure"] = (
                StructureAnalyzer.analyze(work)
            )

        except Exception:

            results["structure"] = {
                "available": False,
                "signal": "NEUTRAL",
                "strength": "WEAK",
            }

        # --------------------------------------------------
        # Support / Resistance
        # --------------------------------------------------

        try:

            results["support_resistance"] = (
                SupportResistanceAnalyzer.analyze(work)
            )

        except Exception:

            results["support_resistance"] = {
                "available": False,
                "signal": "NEUTRAL",
                "strength": "WEAK",
            }

        # ==================================================
        # COMPONENT WEIGHTS
        # ==================================================

        weights = {
            "trend": 35,
            "momentum": 20,
            "candle": 15,
            "volume": 10,
            "structure": 15,
            "support_resistance": 5,
        }

        bullish_score = 0.0
        bearish_score = 0.0

        reasons = []

        component_signals = {}

        for name, result in results.items():

            signal = str(
                result.get(
                    "signal",
                    "NEUTRAL",
                )
            ).upper()

            strength = str(
                result.get(
                    "strength",
                    "WEAK",
                )
            ).upper()

            weight = weights.get(
                name,
                0,
            )

            component_signals[name] = {
                "signal": signal,
                "strength": strength,
            }

            # ------------------------------------------------
            # Strength multiplier
            # ------------------------------------------------

            multiplier = 1.0

            if strength == "VERY_STRONG":

                multiplier = 1.50

            elif strength == "STRONG":

                multiplier = 1.25

            elif strength == "MODERATE":

                multiplier = 1.00

            else:

                multiplier = 0.50

            contribution = (
                weight * multiplier
            )

            if signal in (
                "BULLISH",
                "BUY",
            ):

                bullish_score += contribution

            elif signal in (
                "BEARISH",
                "SELL",
            ):

                bearish_score += contribution

        # ==================================================
        # FINAL TIMEFRAME SIGNAL
        # ==================================================

        difference = (
            bullish_score
            - bearish_score
        )

        if difference >= 15:

            signal = "BULLISH"
            direction = "UP"

        elif difference <= -15:

            signal = "BEARISH"
            direction = "DOWN"

        else:

            signal = "NEUTRAL"
            direction = "SIDEWAYS"

        absolute_difference = abs(
            difference
        )

        if absolute_difference >= 50:

            strength = "VERY_STRONG"

        elif absolute_difference >= 30:

            strength = "STRONG"

        elif absolute_difference >= 15:

            strength = "MODERATE"

        else:

            strength = "WEAK"

        # ==================================================
        # REASONS
        # ==================================================

        if signal == "BULLISH":

            reasons.append(
                f"{self_name(interval)} "
                f"technical pressure is bullish"
            )

        elif signal == "BEARISH":

            reasons.append(
                f"{self_name(interval)} "
                f"technical pressure is bearish"
            )

        else:

            reasons.append(
                f"{self_name(interval)} "
                f"technical pressure is mixed"
            )

        # Add important component reasons.

        for name, result in results.items():

            result_reasons = result.get(
                "reasons",
                [],
            )

            if not isinstance(
                result_reasons,
                list,
            ):

                continue

            for reason in result_reasons[:2]:

                reasons.append(
                    f"{name}: {reason}"
                )

        return {

            "available": True,

            "interval": interval,

            "timeframe": (
                MultiTimeframeAnalyzer
                .TIMEFRAME_NAMES
                .get(
                    interval,
                    interval,
                )
            ),

            "signal": signal,

            "direction": direction,

            "strength": strength,

            "bullish_score": round(
                bullish_score,
                2,
            ),

            "bearish_score": round(
                bearish_score,
                2,
            ),

            "score_difference": round(
                difference,
                2,
            ),

            "components": component_signals,

            "reasons": reasons,

            "rows": len(work),

            "last_datetime": str(
                work["Datetime"].iloc[-1]
                if "Datetime" in work.columns
                else ""
            ),

            "price": round(
                float(
                    work["Close"].iloc[-1]
                ),
                2,
            ),
        }

    # ======================================================
    # MAIN ANALYSIS
    # ======================================================

    @staticmethod
    def analyze(dataframes):

        if not dataframes:

            return {
                "available": False,
                "signal": "NEUTRAL",
                "direction": "SIDEWAYS",
                "strength": "WEAK",
                "alignment": "NO_DATA",
                "available_timeframes": 0,
                "bullish_timeframes": 0,
                "bearish_timeframes": 0,
                "neutral_timeframes": 0,
                "reasons": [
                    "No timeframe data"
                ],
                "timeframes": {},
            }

        results = {}

        bullish = 0
        bearish = 0
        neutral = 0

        available_intervals = []

        # ==================================================
        # ANALYZE EACH TIMEFRAME
        # ==================================================

        for interval in (
            MultiTimeframeAnalyzer.TIMEFRAME_ORDER
        ):

            df = dataframes.get(
                interval
            )

            if df is None or df.empty:

                results[interval] = (
                    MultiTimeframeAnalyzer
                    ._unavailable(
                        "Missing data"
                    )
                )

                continue

            result = (
                MultiTimeframeAnalyzer
                ._analyze_timeframe(
                    df,
                    interval,
                )
            )

            results[interval] = result

            if not result.get(
                "available",
                False,
            ):

                continue

            available_intervals.append(
                interval
            )

            signal = result.get(
                "signal",
                "NEUTRAL",
            )

            if signal == "BULLISH":

                bullish += 1

            elif signal == "BEARISH":

                bearish += 1

            else:

                neutral += 1

        # ==================================================
        # AVAILABLE TIMEFRAMES
        # ==================================================

        available_count = len(
            available_intervals
        )

        # ==================================================
        # ALIGNMENT
        # ==================================================

        if available_count == 0:

            alignment = "NO_DATA"

        elif available_count == 1:

            alignment = "SINGLE_TIMEFRAME"

        elif (
            bullish == available_count
        ):

            alignment = "FULL_BULLISH"

        elif (
            bearish == available_count
        ):

            alignment = "FULL_BEARISH"

        elif bullish > bearish:

            alignment = "BULLISH_BIAS"

        elif bearish > bullish:

            alignment = "BEARISH_BIAS"

        else:

            alignment = "MIXED"

        # ==================================================
        # WEIGHT TIMEFRAMES
        # ==================================================

        timeframe_weights = {
            "1d": 0.50,
            "1h": 0.30,
            "15m": 0.20,
        }

        bullish_score = 0.0
        bearish_score = 0.0

        weighted_reasons = []

        for interval, weight in (
            timeframe_weights.items()
        ):

            result = results.get(
                interval
            )

            if not result:
                continue

            if not result.get(
                "available",
                False,
            ):
                continue

            signal = result.get(
                "signal",
                "NEUTRAL",
            )

            score = max(
                abs(
                    float(
                        result.get(
                            "score_difference",
                            0,
                        )
                    )
                ),
                1.0,
            )

            weighted_score = (
                score * weight
            )

            if signal == "BULLISH":

                bullish_score += (
                    weighted_score
                )

            elif signal == "BEARISH":

                bearish_score += (
                    weighted_score
                )

            weighted_reasons.append(
                f"{interval}: {signal}"
            )

        # ==================================================
        # FINAL MULTI-TIMEFRAME SIGNAL
        # ==================================================

        difference = (
            bullish_score
            - bearish_score
        )

        # Require stronger agreement when
        # several timeframes are available.

        if (
            available_count >= 3
            and bullish == 3
        ):

            signal = "BULLISH"

        elif (
            available_count >= 3
            and bearish == 3
        ):

            signal = "BEARISH"

        elif difference >= 12:

            signal = "BULLISH"

        elif difference <= -12:

            signal = "BEARISH"

        else:

            signal = "NEUTRAL"

        if signal == "BULLISH":

            direction = "UP"

        elif signal == "BEARISH":

            direction = "DOWN"

        else:

            direction = "SIDEWAYS"

        # ==================================================
        # FINAL STRENGTH
        # ==================================================

        absolute_difference = abs(
            difference
        )

        if absolute_difference >= 40:

            strength = "VERY_STRONG"

        elif absolute_difference >= 25:

            strength = "STRONG"

        elif absolute_difference >= 12:

            strength = "MODERATE"

        else:

            strength = "WEAK"

        # ==================================================
        # REASONS
        # ==================================================

        reasons = []

        if available_count < 3:

            missing = [
                interval
                for interval
                in MultiTimeframeAnalyzer.TIMEFRAME_ORDER
                if interval
                not in available_intervals
            ]

            reasons.append(
                "Missing timeframe data: "
                + ", ".join(missing)
            )

        if alignment == "FULL_BULLISH":

            reasons.append(
                "All available timeframes are bullish"
            )

        elif alignment == "FULL_BEARISH":

            reasons.append(
                "All available timeframes are bearish"
            )

        elif alignment == "BULLISH_BIAS":

            reasons.append(
                "Higher number of bullish timeframes"
            )

        elif alignment == "BEARISH_BIAS":

            reasons.append(
                "Higher number of bearish timeframes"
            )

        else:

            reasons.append(
                "Timeframes are not fully aligned"
            )

        # --------------------------------------------------
        # Explicit higher timeframe logic
        # --------------------------------------------------

        daily = results.get("1d")
        hourly = results.get("1h")
        intraday = results.get("15m")

        if (
            daily
            and hourly
            and intraday
            and daily.get("available")
            and hourly.get("available")
            and intraday.get("available")
        ):

            daily_signal = daily.get(
                "signal"
            )

            hourly_signal = hourly.get(
                "signal"
            )

            intraday_signal = intraday.get(
                "signal"
            )

            if (
                daily_signal == "BULLISH"
                and hourly_signal == "BULLISH"
                and intraday_signal == "BULLISH"
            ):

                reasons.append(
                    "Daily + hourly + intraday bullish alignment"
                )

            elif (
                daily_signal == "BEARISH"
                and hourly_signal == "BEARISH"
                and intraday_signal == "BEARISH"
            ):

                reasons.append(
                    "Daily + hourly + intraday bearish alignment"
                )

            else:

                reasons.append(
                    "Higher and lower timeframes disagree"
                )

        # --------------------------------------------------
        # Missing timeframe
        # --------------------------------------------------

        for interval in (
            MultiTimeframeAnalyzer.TIMEFRAME_ORDER
        ):

            result = results.get(
                interval
            )

            if (
                result is not None
                and not result.get(
                    "available",
                    False,
                )
            ):

                reasons.append(
                    f"{interval} timeframe unavailable"
                )

        return {

            "available": (
                available_count > 0
            ),

            "signal": signal,

            "direction": direction,

            "strength": strength,

            "alignment": alignment,

            "available_timeframes": (
                available_count
            ),

            "bullish_timeframes": bullish,

            "bearish_timeframes": bearish,

            "neutral_timeframes": neutral,

            "bullish_score": round(
                bullish_score,
                2,
            ),

            "bearish_score": round(
                bearish_score,
                2,
            ),

            "score_difference": round(
                difference,
                2,
            ),

            "reasons": reasons,

            "timeframes": results,
        }


def self_name(interval):

    return (
        MultiTimeframeAnalyzer
        .TIMEFRAME_NAMES
        .get(
            interval,
            interval,
        )
    )