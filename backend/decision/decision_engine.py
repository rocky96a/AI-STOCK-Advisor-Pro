"""
Final decision engine.

Combines:

    ML prediction
    Technical analysis
    Multi-timeframe analysis
    Safety / contradiction checks

Design goals:

    - Strong MTF alignment has high influence.
    - Strong MTF confirmation can overcome a weak ML disagreement.
    - Strong candle / volume contradictions still protect entries.
    - Low-confidence decisions remain blocked.
    - All numeric values are None/NaN safe.
"""

import math

from backend.ml.predict import Predictor
from backend.analysis.technical_analyzer import TechnicalAnalyzer
from backend.analysis.multi_timeframe_analyzer import (
    MultiTimeframeAnalyzer,
)
from backend.analysis.volatility_analyzer import VolatilityAnalyzer
from backend.analysis.support_resistance_analyzer import (
    SupportResistanceAnalyzer,
)
from backend.utils.trade_levels import compute as trade_levels_compute


class DecisionEngine:

    # ==========================================================
    # CONFIGURATION
    # ==========================================================

    SAFE_CONFIDENCE = 60.0
    STRONG_CONFIDENCE = 70.0

    COMPONENT_WEIGHT = 15.0

    # Weights when MTF data is available.
    ML_WEIGHT = 0.25
    TECHNICAL_WEIGHT = 0.30
    MTF_WEIGHT = 0.45

    # Weights when MTF is unavailable.
    ML_ONLY_WEIGHT = 0.60
    TECHNICAL_ONLY_WEIGHT = 0.40

    # ==========================================================
    # SAFE UTILITIES
    # ==========================================================

    @staticmethod
    def _safe_float(value, default=0.0):
        try:
            if value is None:
                return default

            value = float(value)

            if not math.isfinite(value):
                return default

            return value

        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_text(value, default="NEUTRAL"):
        if value is None:
            return default

        text = str(value).strip().upper()

        if text in {
            "BUY",
            "BULLISH",
            "UP",
        }:
            return "BULLISH"

        if text in {
            "SELL",
            "BEARISH",
            "DOWN",
        }:
            return "BEARISH"

        if text in {
            "HOLD",
            "NEUTRAL",
            "SIDEWAYS",
        }:
            return "NEUTRAL"

        return default

    @staticmethod
    def _safe_strength(value):
        if value is None:
            return "WEAK"

        text = str(value).strip().upper()

        if text in {
            "VERY_STRONG",
            "VERY STRONG",
        }:
            return "VERY_STRONG"

        if text == "STRONG":
            return "STRONG"

        if text == "MODERATE":
            return "MODERATE"

        return "WEAK"

    # ==========================================================
    # COMPONENT SCORING
    # ==========================================================

    @classmethod
    def _component_score(cls, signal, strength):

        signal = cls._safe_text(signal)
        strength = cls._safe_strength(strength)

        multipliers = {
            "VERY_STRONG": 1.00,
            "STRONG": 0.80,
            "MODERATE": 0.55,
            "WEAK": 0.25,
        }

        multiplier = multipliers.get(
            strength,
            0.25,
        )

        score = (
            cls.COMPONENT_WEIGHT
            * multiplier
        )

        if signal == "BULLISH":
            return score

        if signal == "BEARISH":
            return -score

        return 0.0

    # ==========================================================
    # NORMALIZE TECHNICAL COMPONENTS
    # ==========================================================

    @classmethod
    def _normalize_components(cls, technical):

        if not isinstance(technical, dict):
            technical = {}

        raw = technical.get(
            "components",
            {},
        )

        if not isinstance(raw, dict):
            raw = {}

        names = [
            "candle",
            "trend",
            "momentum",
            "volume",
            "volatility",
            "structure",
            "support_resistance",
        ]

        components = {}

        for name in names:

            item = raw.get(
                name,
                {},
            )

            if not isinstance(item, dict):
                item = {}

            signal = cls._safe_text(
                item.get("signal"),
                "NEUTRAL",
            )

            strength = cls._safe_strength(
                item.get("strength"),
            )

            components[name] = {
                "signal": signal,
                "strength": strength,
                "score": cls._component_score(
                    signal,
                    strength,
                ),
            }

        return components

    # ==========================================================
    # COMPONENT COUNTS
    # ==========================================================

    @staticmethod
    def _count_components(components):

        bullish = 0
        bearish = 0
        neutral = 0

        for item in components.values():

            signal = item.get(
                "signal",
                "NEUTRAL",
            )

            if signal == "BULLISH":
                bullish += 1

            elif signal == "BEARISH":
                bearish += 1

            else:
                neutral += 1

        return (
            bullish,
            bearish,
            neutral,
        )

    # ==========================================================
    # TECHNICAL DIRECTION
    # ==========================================================

    @classmethod
    def _technical_direction(
        cls,
        technical,
        components,
    ):

        if not isinstance(technical, dict):
            technical = {}

        signal = cls._safe_text(
            technical.get("signal"),
            "NEUTRAL",
        )

        if signal == "BULLISH":
            return "BUY"

        if signal == "BEARISH":
            return "SELL"

        total_score = sum(
            cls._safe_float(
                item.get("score"),
            )
            for item in components.values()
        )

        if total_score > 10:
            return "BUY"

        if total_score < -10:
            return "SELL"

        return "HOLD"

    # ==========================================================
    # ML PROBABILITIES
    # ==========================================================

    @classmethod
    def _ml_probabilities(cls, ml):

        if not isinstance(ml, dict):
            ml = {}

        probabilities = ml.get(
            "probabilities",
            {},
        )

        if not isinstance(
            probabilities,
            dict,
        ):
            probabilities = {}

        buy = cls._safe_float(
            probabilities.get("BUY"),
            0.0,
        )

        hold = cls._safe_float(
            probabilities.get("HOLD"),
            0.0,
        )

        sell = cls._safe_float(
            probabilities.get("SELL"),
            0.0,
        )

        total = buy + hold + sell

        if total <= 0:

            return {
                "BUY": 0.0,
                "HOLD": 100.0,
                "SELL": 0.0,
            }

        return {
            "BUY": (
                buy / total
            ) * 100.0,

            "HOLD": (
                hold / total
            ) * 100.0,

            "SELL": (
                sell / total
            ) * 100.0,
        }

    # ==========================================================
    # MTF PROBABILITIES
    # ==========================================================

    @classmethod
    def _mtf_probabilities(cls, mtf):

        if not isinstance(mtf, dict):
            mtf = {}

        signal = cls._safe_text(
            mtf.get("signal"),
            "NEUTRAL",
        )

        bullish_score = cls._safe_float(
            mtf.get("bullish_score"),
            0.0,
        )

        bearish_score = cls._safe_float(
            mtf.get("bearish_score"),
            0.0,
        )

        total_score = (
            bullish_score
            + bearish_score
        )

        # --------------------------------------------------
        # Strong explicit alignment
        # --------------------------------------------------

        alignment = str(
            mtf.get(
                "alignment",
                "",
            )
        ).upper()

        if alignment == "FULL_BEARISH":

            return {
                "BUY": 5.0,
                "HOLD": 5.0,
                "SELL": 90.0,
            }

        if alignment == "FULL_BULLISH":

            return {
                "BUY": 90.0,
                "HOLD": 5.0,
                "SELL": 5.0,
            }

        # --------------------------------------------------
        # Score based fallback
        # --------------------------------------------------

        if total_score <= 0:

            if signal == "BULLISH":

                return {
                    "BUY": 70.0,
                    "HOLD": 20.0,
                    "SELL": 10.0,
                }

            if signal == "BEARISH":

                return {
                    "BUY": 10.0,
                    "HOLD": 20.0,
                    "SELL": 70.0,
                }

            return {
                "BUY": 20.0,
                "HOLD": 60.0,
                "SELL": 20.0,
            }

        bullish_percent = (
            bullish_score
            / total_score
        ) * 100.0

        bearish_percent = (
            bearish_score
            / total_score
        ) * 100.0

        hold_percent = max(
            0.0,
            100.0
            - bullish_percent
            - bearish_percent,
        )

        return {
            "BUY": bullish_percent,
            "HOLD": hold_percent,
            "SELL": bearish_percent,
        }

    # ==========================================================
    # TECHNICAL PROBABILITIES
    # ==========================================================

    @classmethod
    def _technical_probabilities(
        cls,
        components,
    ):

        technical_score = sum(
            cls._safe_float(
                item.get("score"),
            )
            for item in components.values()
        )

        max_score = (
            len(components)
            * cls.COMPONENT_WEIGHT
        )

        if max_score <= 0:

            return {
                "BUY": 0.0,
                "HOLD": 100.0,
                "SELL": 0.0,
            }

        percent = (
            technical_score
            / max_score
        ) * 100.0

        buy = max(
            0.0,
            percent,
        )

        sell = max(
            0.0,
            -percent,
        )

        hold = max(
            0.0,
            100.0
            - buy
            - sell,
        )

        return {
            "BUY": buy,
            "HOLD": hold,
            "SELL": sell,
        }

    # ==========================================================
    # NORMALIZE PROBABILITIES
    # ==========================================================

    @classmethod
    def _normalize_probabilities(
        cls,
        probabilities,
    ):

        buy = cls._safe_float(
            probabilities.get("BUY"),
        )

        hold = cls._safe_float(
            probabilities.get("HOLD"),
        )

        sell = cls._safe_float(
            probabilities.get("SELL"),
        )

        total = (
            buy
            + hold
            + sell
        )

        if total <= 0:

            return {
                "BUY": 0.0,
                "HOLD": 100.0,
                "SELL": 0.0,
            }

        return {
            "BUY": (
                buy / total
            ) * 100.0,

            "HOLD": (
                hold / total
            ) * 100.0,

            "SELL": (
                sell / total
            ) * 100.0,
        }

    # ==========================================================
    # MTF DIRECTION
    # ==========================================================

    @classmethod
    def _mtf_direction(cls, mtf):

        if not isinstance(mtf, dict):
            return "HOLD"

        signal = cls._safe_text(
            mtf.get("signal"),
            "NEUTRAL",
        )

        if signal == "BULLISH":
            return "BUY"

        if signal == "BEARISH":
            return "SELL"

        return "HOLD"

    # ==========================================================
    # STRENGTH
    # ==========================================================

    @classmethod
    def _final_strength(
        cls,
        confidence,
        mtf,
        final_signal,
    ):

        confidence = cls._safe_float(
            confidence,
        )

        alignment = str(
            mtf.get(
                "alignment",
                "",
            )
        ).upper()

        if (
            alignment
            in {
                "FULL_BEARISH",
                "FULL_BULLISH",
            }
            and final_signal
            in {
                "BUY",
                "SELL",
            }
            and confidence >= 70
        ):
            return "STRONG"

        if confidence >= 70:
            return "STRONG"

        if confidence >= 55:
            return "MODERATE"

        return "WEAK"

    # ==========================================================
    # BUILD REASONS
    # ==========================================================

    @classmethod
    def _build_reasons(
        cls,
        ml,
        technical,
        mtf,
        components,
        final_signal,
        final_confidence,
    ):

        reasons = []

        ml_signal = cls._safe_text(
            ml.get("signal"),
            "HOLD",
        )

        technical_signal = cls._safe_text(
            technical.get("signal"),
            "HOLD",
        )

        # --------------------------------------------------
        # ML
        # --------------------------------------------------

        if ml_signal == "BULLISH":

            reasons.append(
                "ML model favored BUY"
            )

        elif ml_signal == "BEARISH":

            reasons.append(
                "ML model favored SELL"
            )

        else:

            reasons.append(
                "ML model favored HOLD"
            )

        # --------------------------------------------------
        # Technical
        # --------------------------------------------------

        reasons.append(
            f"Technical engine: "
            f"{technical_signal}"
        )

        bullish, bearish, neutral = (
            cls._count_components(
                components
            )
        )

        if bullish:

            reasons.append(
                f"{bullish} technical "
                f"components are bullish"
            )

        if bearish:

            reasons.append(
                f"{bearish} technical "
                f"components are bearish"
            )

        if neutral:

            reasons.append(
                f"{neutral} technical "
                f"components are neutral"
            )

        # --------------------------------------------------
        # Candle
        # --------------------------------------------------

        candle = components["candle"]

        if (
            candle["signal"] == "BEARISH"
            and candle["strength"]
            in {
                "STRONG",
                "VERY_STRONG",
            }
        ):

            reasons.append(
                "Strong bearish candlestick pressure"
            )

        elif (
            candle["signal"] == "BULLISH"
            and candle["strength"]
            in {
                "STRONG",
                "VERY_STRONG",
            }
        ):

            reasons.append(
                "Strong bullish candlestick pressure"
            )

        # --------------------------------------------------
        # Volume
        # --------------------------------------------------

        volume = components["volume"]

        if volume["signal"] == "BEARISH":

            reasons.append(
                "Volume confirms bearish pressure"
            )

        elif volume["signal"] == "BULLISH":

            reasons.append(
                "Volume confirms bullish pressure"
            )

        # --------------------------------------------------
        # Structure
        # --------------------------------------------------

        structure = components["structure"]

        if structure["signal"] == "BULLISH":

            reasons.append(
                "Market structure is bullish"
            )

        elif structure["signal"] == "BEARISH":

            reasons.append(
                "Market structure is bearish"
            )

        # --------------------------------------------------
        # MTF
        # --------------------------------------------------

        mtf_signal = cls._safe_text(
            mtf.get("signal"),
            "NEUTRAL",
        )

        alignment = str(
            mtf.get(
                "alignment",
                "NO_DATA",
            )
        ).upper()

        if alignment == "FULL_BEARISH":

            reasons.append(
                "Daily + hourly + intraday "
                "are bearish"
            )

        elif alignment == "FULL_BULLISH":

            reasons.append(
                "Daily + hourly + intraday "
                "are bullish"
            )

        elif mtf_signal == "BEARISH":

            reasons.append(
                "Multi-timeframe analysis "
                "is bearish"
            )

        elif mtf_signal == "BULLISH":

            reasons.append(
                "Multi-timeframe analysis "
                "is bullish"
            )

        # --------------------------------------------------
        # Conflict
        # --------------------------------------------------

        if (
            ml_signal == "BULLISH"
            and final_signal == "SELL"
        ):

            reasons.append(
                "ML BUY disagrees with "
                "stronger technical/MTF SELL pressure"
            )

        elif (
            ml_signal == "BEARISH"
            and final_signal == "BUY"
        ):

            reasons.append(
                "ML SELL disagrees with "
                "stronger technical/MTF BUY pressure"
            )

        # --------------------------------------------------
        # Confidence
        # --------------------------------------------------

        if (
            final_confidence
            < cls.SAFE_CONFIDENCE
        ):

            reasons.append(
                "Decision confidence is below "
                "safe threshold"
            )

        return reasons

    # ==========================================================
    # CONTRADICTIONS
    # ==========================================================

    @classmethod
    def _detect_contradictions(
        cls,
        ml,
        components,
        mtf,
        final_signal,
    ):

        warnings = []

        ml_signal = cls._safe_text(
            ml.get("signal"),
            "HOLD",
        )

        candle = components["candle"]
        volume = components["volume"]
        trend = components["trend"]

        # --------------------------------------------------
        # Candle
        # --------------------------------------------------

        if (
            final_signal == "BUY"
            and candle["signal"] == "BEARISH"
            and candle["strength"]
            == "VERY_STRONG"
        ):

            warnings.append(
                "Very strong bearish candlestick "
                "opposes BUY"
            )

        if (
            final_signal == "SELL"
            and candle["signal"] == "BULLISH"
            and candle["strength"]
            == "VERY_STRONG"
        ):

            warnings.append(
                "Very strong bullish candlestick "
                "opposes SELL"
            )

        # --------------------------------------------------
        # Volume
        # --------------------------------------------------

        if (
            final_signal == "BUY"
            and volume["signal"] == "BEARISH"
        ):

            warnings.append(
                "Volume confirms bearish pressure "
                "against BUY"
            )

        if (
            final_signal == "SELL"
            and volume["signal"] == "BULLISH"
        ):

            warnings.append(
                "Volume confirms bullish pressure "
                "against SELL"
            )

        # --------------------------------------------------
        # Trend
        # --------------------------------------------------

        if (
            final_signal == "BUY"
            and trend["signal"] == "BEARISH"
            and trend["strength"]
            in {
                "STRONG",
                "VERY_STRONG",
            }
        ):

            warnings.append(
                "Strong bearish trend opposes BUY"
            )

        if (
            final_signal == "SELL"
            and trend["signal"] == "BULLISH"
            and trend["strength"]
            in {
                "STRONG",
                "VERY_STRONG",
            }
        ):

            warnings.append(
                "Strong bullish trend opposes SELL"
            )

        # --------------------------------------------------
        # ML
        # --------------------------------------------------

        if (
            ml_signal == "BULLISH"
            and final_signal == "SELL"
        ):

            warnings.append(
                "ML BUY signal conflicts with "
                "technical SELL pressure"
            )

        elif (
            ml_signal == "BEARISH"
            and final_signal == "BUY"
        ):

            warnings.append(
                "ML SELL signal conflicts with "
                "technical BUY pressure"
            )

        # --------------------------------------------------
        # MTF
        # --------------------------------------------------

        mtf_signal = cls._safe_text(
            mtf.get("signal"),
            "NEUTRAL",
        )

        if (
            mtf_signal == "BEARISH"
            and final_signal == "BUY"
        ):

            warnings.append(
                "Multi-timeframe bearish pressure "
                "conflicts with BUY"
            )

        elif (
            mtf_signal == "BULLISH"
            and final_signal == "SELL"
        ):

            warnings.append(
                "Multi-timeframe bullish pressure "
                "conflicts with SELL"
            )

        return warnings

    # ==========================================================
    # SAFETY ADJUSTMENT
    # ==========================================================

    @classmethod
    def _apply_safety(
        cls,
        final_signal,
        final_confidence,
        probabilities,
        components,
        mtf,
    ):

        blocked = False
        safety_reasons = []

        alignment = str(
            mtf.get(
                "alignment",
                "NO_DATA",
            )
        ).upper()

        candle = components["candle"]
        volume = components["volume"]

        # --------------------------------------------------
        # FULL MTF AGAINST DECISION
        #
        # This is a true safety block.
        #
        # We do NOT block a SELL because MTF is bearish.
        # We do NOT block a BUY because MTF is bullish.
        # Those are confirmations.
        # --------------------------------------------------

        if (
            final_signal == "BUY"
            and alignment == "FULL_BEARISH"
        ):

            blocked = True

            safety_reasons.append(
                "All timeframes are bearish "
                "against BUY"
            )

            final_signal = "HOLD"

            final_confidence = max(
                cls._safe_float(
                    probabilities.get("HOLD"),
                ),
                50.0,
            )

        elif (
            final_signal == "SELL"
            and alignment == "FULL_BULLISH"
        ):

            blocked = True

            safety_reasons.append(
                "All timeframes are bullish "
                "against SELL"
            )

            final_signal = "HOLD"

            final_confidence = max(
                cls._safe_float(
                    probabilities.get("HOLD"),
                ),
                50.0,
            )

        # --------------------------------------------------
        # VERY STRONG CANDLE
        # --------------------------------------------------

        if (
            final_signal == "BUY"
            and candle["signal"] == "BEARISH"
            and candle["strength"]
            == "VERY_STRONG"
            and final_confidence < 70
        ):

            blocked = True

            safety_reasons.append(
                "Very strong bearish candlestick "
                "opposes BUY"
            )

            final_signal = "HOLD"

            final_confidence = max(
                cls._safe_float(
                    probabilities.get("HOLD"),
                ),
                50.0,
            )

        elif (
            final_signal == "SELL"
            and candle["signal"] == "BULLISH"
            and candle["strength"]
            == "VERY_STRONG"
            and final_confidence < 70
        ):

            blocked = True

            safety_reasons.append(
                "Very strong bullish candlestick "
                "opposes SELL"
            )

            final_signal = "HOLD"

            final_confidence = max(
                cls._safe_float(
                    probabilities.get("HOLD"),
                ),
                50.0,
            )

        # --------------------------------------------------
        # VOLUME
        # --------------------------------------------------

        if (
            final_signal == "BUY"
            and volume["signal"] == "BEARISH"
            and volume["strength"]
            in {
                "STRONG",
                "VERY_STRONG",
            }
            and final_confidence < 70
        ):

            blocked = True

            safety_reasons.append(
                "Volume confirms bearish pressure "
                "against BUY"
            )

            final_signal = "HOLD"

            final_confidence = max(
                cls._safe_float(
                    probabilities.get("HOLD"),
                ),
                50.0,
            )

        elif (
            final_signal == "SELL"
            and volume["signal"] == "BULLISH"
            and volume["strength"]
            in {
                "STRONG",
                "VERY_STRONG",
            }
            and final_confidence < 70
        ):

            blocked = True

            safety_reasons.append(
                "Volume confirms bullish pressure "
                "against SELL"
            )

            final_signal = "HOLD"

            final_confidence = max(
                cls._safe_float(
                    probabilities.get("HOLD"),
                ),
                50.0,
            )

        # --------------------------------------------------
        # LOW CONFIDENCE
        # --------------------------------------------------

        if (
            final_confidence
            < cls.SAFE_CONFIDENCE
        ):

            blocked = True

            safety_reasons.append(
                "Decision confidence is below "
                "safe threshold"
            )

        return (
            final_signal,
            final_confidence,
            blocked,
            safety_reasons,
        )

    # ==========================================================
    # FINAL ANALYSIS
    # ==========================================================

    @classmethod
    def analyze(
        cls,
        df,
        symbol,
        model_name=None,
        dataframes=None,
    ):

        # ==================================================
        # ML
        # ==================================================

        ml = Predictor.predict(
            df,
            symbol,
            model_name=model_name,
        )

        if not ml.get(
            "available",
            False,
        ):

            return {
                "available": False,
                "symbol": symbol,
                "signal": "HOLD",
                "direction": "SIDEWAYS",
                "strength": "WEAK",
                "confidence": 0.0,
                "probabilities": {
                    "BUY": 0.0,
                    "HOLD": 100.0,
                    "SELL": 0.0,
                },
                "blocked": True,
                "reasons": [
                    ml.get(
                        "reason",
                        "ML prediction unavailable.",
                    )
                ],
            }

        # ==================================================
        # TECHNICAL
        # ==================================================

        technical = TechnicalAnalyzer.analyze(
            df
        )

        if not technical.get(
            "available",
            False,
        ):

            return {
                "available": False,
                "symbol": symbol,
                "signal": "HOLD",
                "direction": "SIDEWAYS",
                "strength": "WEAK",
                "confidence": 0.0,
                "probabilities": {
                    "BUY": 0.0,
                    "HOLD": 100.0,
                    "SELL": 0.0,
                },
                "blocked": True,
                "reasons": [
                    technical.get(
                        "reason",
                        "Technical analysis unavailable.",
                    )
                ],
            }

        # ==================================================
        # COMPONENTS
        # ==================================================

        components = (
            cls._normalize_components(
                technical
            )
        )

        bullish_count, bearish_count, neutral_count = (
            cls._count_components(
                components
            )
        )

        # ==================================================
        # PROBABILITIES
        # ==================================================

        ml_probs = cls._ml_probabilities(
            ml
        )

        technical_probs = (
            cls._technical_probabilities(
                components
            )
        )

        # ==================================================
        # MULTI TIMEFRAME
        # ==================================================

        if dataframes:

            mtf = (
                MultiTimeframeAnalyzer.analyze(
                    dataframes
                )
            )

        else:

            mtf = {
                "available": False,
                "signal": "NEUTRAL",
                "direction": "SIDEWAYS",
                "strength": "WEAK",
                "alignment": "NO_DATA",
                "available_timeframes": 0,
                "bullish_timeframes": 0,
                "bearish_timeframes": 0,
                "neutral_timeframes": 0,
                "bullish_score": 0.0,
                "bearish_score": 0.0,
                "score_difference": 0.0,
                "reasons": [
                    "Multi-timeframe data not supplied"
                ],
                "timeframes": {},
            }

        mtf_probs = cls._mtf_probabilities(
            mtf
        )

        mtf_available = bool(
            mtf.get(
                "available",
                False,
            )
        )

        # ==================================================
        # COMBINE
        # ==================================================

        if mtf_available:

            combined = {
                "BUY": (
                    ml_probs["BUY"]
                    * cls.ML_WEIGHT
                    + technical_probs["BUY"]
                    * cls.TECHNICAL_WEIGHT
                    + mtf_probs["BUY"]
                    * cls.MTF_WEIGHT
                ),

                "HOLD": (
                    ml_probs["HOLD"]
                    * cls.ML_WEIGHT
                    + technical_probs["HOLD"]
                    * cls.TECHNICAL_WEIGHT
                    + mtf_probs["HOLD"]
                    * cls.MTF_WEIGHT
                ),

                "SELL": (
                    ml_probs["SELL"]
                    * cls.ML_WEIGHT
                    + technical_probs["SELL"]
                    * cls.TECHNICAL_WEIGHT
                    + mtf_probs["SELL"]
                    * cls.MTF_WEIGHT
                ),
            }

        else:

            combined = {
                "BUY": (
                    ml_probs["BUY"]
                    * cls.ML_ONLY_WEIGHT
                    + technical_probs["BUY"]
                    * cls.TECHNICAL_ONLY_WEIGHT
                ),

                "HOLD": (
                    ml_probs["HOLD"]
                    * cls.ML_ONLY_WEIGHT
                    + technical_probs["HOLD"]
                    * cls.TECHNICAL_ONLY_WEIGHT
                ),

                "SELL": (
                    ml_probs["SELL"]
                    * cls.ML_ONLY_WEIGHT
                    + technical_probs["SELL"]
                    * cls.TECHNICAL_ONLY_WEIGHT
                ),
            }

        probabilities_raw = (
            cls._normalize_probabilities(
                combined
            )
        )

        probabilities = {
            key: round(
                value,
                2,
            )
            for key, value
            in probabilities_raw.items()
        }

        # ==================================================
        # PRELIMINARY SIGNAL
        # ==================================================

        preliminary_signal = max(
            probabilities,
            key=probabilities.get,
        )

        preliminary_confidence = (
        cls._safe_float(
            probabilities.get(
                preliminary_signal
            )
        )
    )

        # ======================================================
         # TECHNICAL DIRECTION
         # ======================================================

        technical_direction = (
        cls._technical_direction(
            technical,
            components,
        )
    )
        # ==================================================
        # STRONG MTF OVERRIDE
        #
        # Only when the MTF alignment is complete.
        #
        # This makes the system recognize:
        #
        # 1d bearish
        # 1h bearish
        # 15m bearish
        #
        # as a meaningful SELL confirmation.
        # ==================================================

        alignment = str(
            mtf.get(
                "alignment",
                "NO_DATA",
            )
        ).upper()

        final_signal = preliminary_signal

        if alignment == "FULL_BEARISH":

            # If BUY wins only because ML is bullish,
            # complete bearish MTF alignment gets priority.
            if (
                ml_probs["BUY"]
                > ml_probs["SELL"]
                and preliminary_signal != "SELL"
            ):

                final_signal = "SELL"

        elif alignment == "FULL_BULLISH":

            if (
                ml_probs["SELL"]
                > ml_probs["BUY"]
                and preliminary_signal != "BUY"
            ):

                final_signal = "BUY"

        final_confidence = cls._safe_float(
            probabilities.get(
                final_signal,
            ),
        )

        # ==================================================
        # CONFIDENCE BOOST FOR COMPLETE ALIGNMENT
        #
        # Do not blindly set confidence to 90.
        # Instead, use the existing probability plus
        # a controlled alignment bonus.
        # ==================================================

        if (
            final_signal == "SELL"
            and alignment == "FULL_BEARISH"
        ):

            mtf_strength = str(
                mtf.get(
                    "strength",
                    "WEAK",
                )
            ).upper()

            if mtf_strength in {
                "VERY_STRONG",
                "STRONG",
            }:

                final_confidence = max(
                    final_confidence,
                    60.0,
                )

        elif (
            final_signal == "BUY"
            and alignment == "FULL_BULLISH"
        ):

            mtf_strength = str(
                mtf.get(
                    "strength",
                    "WEAK",
                )
            ).upper()

            if mtf_strength in {
                "VERY_STRONG",
                "STRONG",
            }:

                final_confidence = max(
                    final_confidence,
                    60.0,
                )

        # ==================================================
        # CONTRADICTIONS
        # ==================================================

        contradiction_warnings = (
            cls._detect_contradictions(
                ml,
                components,
                mtf,
                final_signal,
            )
        )

        # ==================================================
        # SAFETY
        # ==================================================

        (
            final_signal,
            final_confidence,
            blocked,
            safety_reasons,
        ) = cls._apply_safety(
            final_signal,
            final_confidence,
            probabilities,
            components,
            mtf,
        )

        # ==================================================
        # DIRECTION
        # ==================================================

        if final_signal == "BUY":

            direction = "UP"

        elif final_signal == "SELL":

            direction = "DOWN"

        else:

            direction = "SIDEWAYS"

        # ==================================================
        # STRENGTH
        # ==================================================

        strength = cls._final_strength(
            final_confidence,
            mtf,
            final_signal,
        )

        # ==================================================
        # REASONS
        # ==================================================

        reasons = cls._build_reasons(
            ml,
            technical,
            mtf,
            components,
            final_signal,
            final_confidence,
        )

        # Add contradiction warnings.

        for warning in contradiction_warnings:

            if warning not in reasons:

                reasons.append(
                    warning
                )

        # Add safety reasons.

        for reason in safety_reasons:

            if reason not in reasons:

                reasons.append(
                    reason
                )

        # ==================================================
        # TRADE LEVELS
        #
        # Entry / stop-loss / target1 / target2 / risk-reward,
        # anchored to real support/resistance structure rather
        # than a raw ATR projection. HOLD or blocked signals
        # get no trade levels (there is nothing to enter).
        # ==================================================

        trade_levels = {
            "entry": None,
            "stoploss": None,
            "target1": None,
            "target2": None,
            "risk_reward": None,
            "risk_percent": None,
        }

        if not blocked and final_signal in ("BUY", "STRONG BUY", "SELL", "STRONG SELL"):

            try:

                last_price = cls._safe_float(
                    df["Close"].iloc[-1]
                    if df is not None and not df.empty
                    else None
                )

                volatility = VolatilityAnalyzer.analyze(df)

                atr = cls._safe_float(
                    volatility.get("atr")
                    if volatility.get("available", False)
                    else None
                )

                sr = SupportResistanceAnalyzer.analyze(df)

                # SupportResistanceAnalyzer returns levels as dicts,
                # e.g. {"price": 127.52, "touches": 7} — trade_levels.compute()
                # expects plain floats, nearest-to-price first.
                def _extract_prices(levels):
                    out = []
                    for lvl in levels or []:
                        if isinstance(lvl, dict):
                            price = lvl.get("price")
                        else:
                            price = lvl
                        price = cls._safe_float(price, default=None)
                        if price is not None:
                            out.append(price)
                    return out

                resistances = _extract_prices(sr.get("resistance_levels"))
                supports = _extract_prices(sr.get("support_levels"))

                if last_price > 0 and atr > 0:

                    trade_levels = trade_levels_compute(
                        signal=final_signal,
                        price=last_price,
                        atr=atr,
                        resistances=resistances,
                        supports=supports,
                    )

                    # Entry reference point — the candle this verdict was
                    # generated on. Lets the frontend mark exactly where
                    # on the chart the signal fired.
                    if df is not None and not df.empty:
                        entry_ts = df.index[-1]
                        trade_levels["entry_index"] = len(df) - 1
                        trade_levels["entry_time"] = (
                            entry_ts.isoformat()
                            if hasattr(entry_ts, "isoformat")
                            else str(entry_ts)
                        )

                elif last_price <= 0:
                    reasons.append("Trade levels unavailable: no valid last price.")
                elif atr <= 0:
                    reasons.append("Trade levels unavailable: ATR could not be computed (insufficient candles).")

            except Exception as exc:

                # Surface the failure as its own flagged reason instead of
                # a generic chip that can get silently cut off in the UI.
                reasons.insert(
                    0,
                    f"⚠ Trade levels failed: {exc}",
                )

        # ==================================================
        # RESULT
        # ==================================================

        return {
            "available": True,

            "symbol": symbol,

            "signal": final_signal,

            "entry": trade_levels.get("entry"),
            "stoploss": trade_levels.get("stoploss"),
            "target1": trade_levels.get("target1"),
            "target2": trade_levels.get("target2"),
            "risk_reward": trade_levels.get("risk_reward"),
            "risk_percent": trade_levels.get("risk_percent"),
            "entry_index": trade_levels.get("entry_index"),
            "entry_time": trade_levels.get("entry_time"),

            "direction": direction,

            "strength": strength,

            "confidence": round(
                final_confidence,
                2,
            ),

            "blocked": blocked,

            "probabilities": probabilities,

            "ml": {
                "available": bool(
                    ml.get(
                        "available",
                        False,
                    )
                ),

                "signal": cls._safe_text(
                    ml.get(
                        "signal",
                        "HOLD",
                    ),
                    "HOLD",
                ),

                "confidence": round(
                    cls._safe_float(
                        ml.get(
                            "confidence",
                            0.0,
                        )
                    ),
                    2,
                ),

                "probabilities": {
                    key: round(
                        value,
                        2,
                    )
                    for key, value
                    in ml_probs.items()
                },
            },

            "technical": {
                "available": bool(
                    technical.get(
                        "available",
                        True,
                    )
                ),

                "signal": cls._safe_text(
                    technical.get(
                        "signal",
                        "HOLD",
                    ),
                    "HOLD",
                ),

                "direction": (
                    technical_direction
                ),

                "score": round(
                    sum(
                        item["score"]
                        for item
                        in components.values()
                    ),
                    2,
                ),

                "components": components,

                "bullish_components": (
                    bullish_count
                ),

                "bearish_components": (
                    bearish_count
                ),

                "neutral_components": (
                    neutral_count
                ),
            },

            "multi_timeframe": mtf,

            "reasons": reasons,

            "safety": {
                "blocked": blocked,
                "reasons": safety_reasons,
            },
        }