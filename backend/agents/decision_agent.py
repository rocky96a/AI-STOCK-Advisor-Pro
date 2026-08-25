from backend.utils.trade_levels import compute as compute_trade_levels


"""
Decision Agent

Combines:
    1. Technical analysis
    2. ML prediction
    3. Market structure
    4. Candlestick confirmation
    5. Momentum
    6. Volume
    7. Support / resistance
    8. ATR risk management

Decision philosophy:

    - Technical analysis is the primary signal.
    - ML is a confirmation layer.
    - ML HOLD / SIDEWAYS is neutral.
    - Direct technical/ML disagreement produces WAIT.
    - Poor risk/reward produces WAIT.
"""


# ============================================================
# Configuration
# ============================================================

TECH_WEIGHT = 0.60
ML_WEIGHT = 0.40

MAX_TECHNICAL_CONFIDENCE = 90.0
MIN_RISK_REWARD = 1.0
WAIT_MAX_CONFIDENCE = 60.0


# ============================================================
# Utility Functions
# ============================================================

def _clamp(
    value,
    minimum=0.0,
    maximum=100.0,
):
    """
    Keep a numeric value inside a safe range.
    """

    try:
        value = float(value)
    except (TypeError, ValueError):
        return minimum

    return max(
        minimum,
        min(value, maximum),
    )


# ============================================================
# Holding Period
# ============================================================

def _holding_period_estimate(
    entry,
    target1,
    atr,
):
    """
    Estimate the number of trading days required
    to reach target1.

    This is a heuristic only.
    It is NOT a guaranteed exit-date prediction.
    """

    if (
        entry is None
        or target1 is None
        or atr in (None, 0)
    ):
        return None

    try:
        entry = float(entry)
        target1 = float(target1)
        atr = float(atr)
    except (TypeError, ValueError):
        return None

    distance = abs(
        target1 - entry
    )

    # Conservative assumption:
    # approximately 40% of ATR is captured per day.
    daily_progress = atr * 0.40

    if daily_progress <= 0:
        return None

    days = distance / daily_progress

    low = max(
        1,
        round(days * 0.60),
    )

    high = max(
        low,
        round(days * 1.60),
    )

    return {
        "estimated_days": round(
            days,
            1,
        ),
        "estimated_range": (
            f"{low}-{high} trading days"
        ),
    }


# ============================================================
# Technical Confidence
# ============================================================

def _technical_confidence(
    technical_result,
):
    """
    Use the confidence already calculated by TechnicalAgent.

    Do not calculate a second incompatible confidence here.
    """

    confidence = technical_result.get(
        "confidence"
    )

    if confidence is None:
        return 0.0

    return round(
        _clamp(
            confidence,
            0.0,
            MAX_TECHNICAL_CONFIDENCE,
        ),
        2,
    )


# ============================================================
# Technical Components
# ============================================================

def _get_component(
    technical_result,
    name,
):
    """
    Safely retrieve one technical component.
    """

    components = technical_result.get(
        "components",
        {},
    )

    if not isinstance(
        components,
        dict,
    ):
        return {}

    component = components.get(
        name,
        {},
    )

    if not isinstance(
        component,
        dict,
    ):
        return {}

    return component


# ============================================================
# Risk Levels
# ============================================================

def _risk_levels(
    signal,
    entry,
    atr,
    support_resistance=None,
):
    """
    Build trade levels using the shared
    technical trade-level engine.

    These are planning levels,
    not guaranteed future prices.
    """

    if (
        entry is None
        or atr in (None, 0)
    ):
        return {
            "entry": entry,
            "stoploss": None,
            "target1": None,
            "target2": None,
            "risk_reward": None,
            "risk_percent": None,
        }

    try:
        entry = float(entry)
        atr = float(atr)
    except (
        TypeError,
        ValueError,
    ):
        return {
            "entry": entry,
            "stoploss": None,
            "target1": None,
            "target2": None,
            "risk_reward": None,
            "risk_percent": None,
        }

    supports = []
    resistances = []

    if isinstance(
        support_resistance,
        dict,
    ):

        supports = [
            float(level["price"])
            for level in support_resistance.get(
                "support_levels",
                [],
            )
            if (
                isinstance(level, dict)
                and level.get("price") is not None
            )
        ]

        resistances = [
            float(level["price"])
            for level in support_resistance.get(
                "resistance_levels",
                [],
            )
            if (
                isinstance(level, dict)
                and level.get("price") is not None
            )
        ]

    return compute_trade_levels(
        signal=signal,
        price=entry,
        atr=atr,
        resistances=resistances,
        supports=supports,
    )


# ============================================================
# Signal Direction Helpers
# ============================================================

def _is_technical_buy(signal):
    return signal in (
        "BUY",
        "BULLISH",
        "STRONG BUY",
    )


def _is_technical_sell(signal):
    return signal in (
        "SELL",
        "BEARISH",
        "STRONG SELL",
    )


def _is_ml_buy(
    ml_signal,
    ml_direction,
):
    return (
        ml_direction == "UP"
        or ml_signal == "BUY"
    )


def _is_ml_sell(
    ml_signal,
    ml_direction,
):
    return (
        ml_direction == "DOWN"
        or ml_signal == "SELL"
    )


# ============================================================
# ML / Technical Decision
# ============================================================

def _calculate_signal_confidence(
    technical_signal,
    technical_confidence,
    ml_available,
    ml_signal,
    ml_direction,
    ml_confidence,
):
    """
    Calculate final confidence.

    Rules:

        Technical BUY + ML BUY
            -> weighted confirmation

        Technical SELL + ML SELL
            -> weighted confirmation

        Technical BUY + ML SELL
            -> conflict, reduce confidence

        Technical SELL + ML BUY
            -> conflict, reduce confidence

        Technical BUY/SELL + ML HOLD/SIDEWAYS
            -> technical confidence only

        No clear technical signal
            -> technical confidence only
    """

    technical_is_buy = _is_technical_buy(
        technical_signal
    )

    technical_is_sell = _is_technical_sell(
        technical_signal
    )

    if not ml_available:

        return {
            "confidence": technical_confidence,
            "mode": "TECHNICAL_ONLY",
            "agreement": None,
            "conflict": False,
        }

    ml_is_buy = _is_ml_buy(
        ml_signal,
        ml_direction,
    )

    ml_is_sell = _is_ml_sell(
        ml_signal,
        ml_direction,
    )

    # --------------------------------------------------------
    # Technical BUY
    # --------------------------------------------------------

    if technical_is_buy:

        if ml_is_buy:

            confidence = (
                technical_confidence
                * TECH_WEIGHT
                + ml_confidence
                * ML_WEIGHT
            )

            return {
                "confidence": confidence,
                "mode": "TECHNICAL_ML_CONFIRMED",
                "agreement": True,
                "conflict": False,
            }

        if ml_is_sell:

            confidence = (
                technical_confidence
                * 0.55
            )

            return {
                "confidence": confidence,
                "mode": "TECHNICAL_ML_CONFLICT",
                "agreement": False,
                "conflict": True,
            }

        # ML HOLD / SIDEWAYS
        return {
            "confidence": technical_confidence,
            "mode": "TECHNICAL_CONFIRMED_ML_NEUTRAL",
            "agreement": False,
            "conflict": False,
        }

    # --------------------------------------------------------
    # Technical SELL
    # --------------------------------------------------------

    if technical_is_sell:

        if ml_is_sell:

            confidence = (
                technical_confidence
                * TECH_WEIGHT
                + ml_confidence
                * ML_WEIGHT
            )

            return {
                "confidence": confidence,
                "mode": "TECHNICAL_ML_CONFIRMED",
                "agreement": True,
                "conflict": False,
            }

        if ml_is_buy:

            confidence = (
                technical_confidence
                * 0.55
            )

            return {
                "confidence": confidence,
                "mode": "TECHNICAL_ML_CONFLICT",
                "agreement": False,
                "conflict": True,
            }

        # ML HOLD / SIDEWAYS
        return {
            "confidence": technical_confidence,
            "mode": "TECHNICAL_CONFIRMED_ML_NEUTRAL",
            "agreement": False,
            "conflict": False,
        }

    # --------------------------------------------------------
    # No clear technical direction
    # --------------------------------------------------------

    return {
        "confidence": technical_confidence,
        "mode": "NO_CLEAR_TECHNICAL_SIGNAL",
        "agreement": None,
        "conflict": False,
    }


# ============================================================
# Reasons
# ============================================================

def _build_component_reasons(
    reasons,
    candle_signal,
    momentum_signal,
    volume_signal,
    structure_signal,
    volatility_state,
    breakout,
    breakdown,
    technical_is_buy,
    technical_is_sell,
):
    """
    Add technical component explanations.
    """

    # Candlestick
    if candle_signal == "BULLISH":

        reasons.append(
            "Candlestick analysis is bullish."
        )

    elif candle_signal == "BEARISH":

        reasons.append(
            "Candlestick analysis is bearish."
        )

    # Momentum
    if momentum_signal == "BULLISH":

        reasons.append(
            "Momentum is bullish."
        )

    elif momentum_signal == "BEARISH":

        reasons.append(
            "Momentum is bearish."
        )

    # Volume
    if volume_signal == "BULLISH":

        reasons.append(
            "Volume confirms bullish pressure."
        )

    elif volume_signal == "BEARISH":

        reasons.append(
            "Volume confirms bearish pressure."
        )

    # Structure
    if structure_signal == "BULLISH":

        reasons.append(
            "Market structure is bullish."
        )

    elif structure_signal == "BEARISH":

        reasons.append(
            "Market structure is bearish."
        )

    # Structure conflict
    if (
        technical_is_buy
        and structure_signal == "BEARISH"
    ):

        reasons.append(
            "Bullish setup conflicts with "
            "bearish market structure."
        )

    elif (
        technical_is_sell
        and structure_signal == "BULLISH"
    ):

        reasons.append(
            "Bearish setup conflicts with "
            "bullish market structure."
        )

    # Volatility
    if volatility_state:

        reasons.append(
            f"Volatility state: "
            f"{volatility_state}."
        )

    # Breakout
    if breakout:

        reasons.append(
            "Resistance breakout detected."
        )

    # Breakdown
    if breakdown:

        reasons.append(
            "Support breakdown detected."
        )


# ============================================================
# Main Decision Agent
# ============================================================

class DecisionAgent:

    @staticmethod
    def decide(
        technical_result,
        ml_result,
        price,
        atr,
    ):
        """
        Produce the final trading decision.

        Possible final signals:

            BUY
            SELL
            WAIT

        WAIT is used when:

            - technical/ML signals conflict
            - there is no clear technical signal
            - risk/reward is too poor
        """

        # ====================================================
        # Validate Technical Result
        # ====================================================

        if not isinstance(
            technical_result,
            dict,
        ):

            return {
                "available": False,
                "reason": (
                    "Invalid technical analysis."
                ),
            }

        # ====================================================
        # Basic Technical Data
        # ====================================================

        technical_signal = technical_result.get(
            "signal",
            "HOLD",
        )

        technical_strength = technical_result.get(
            "strength",
            "WEAK",
        )

        technical_confidence = (
            _technical_confidence(
                technical_result
            )
        )

        technical_is_buy = _is_technical_buy(
            technical_signal
        )

        technical_is_sell = _is_technical_sell(
            technical_signal
        )

        # ====================================================
        # ML Data
        # ====================================================

        ml_available = bool(
            ml_result
            and ml_result.get(
                "available",
                False,
            )
        )

        ml_signal = (
            ml_result.get("signal")
            if ml_available
            else None
        )

        ml_direction = (
            ml_result.get("direction")
            if ml_available
            else None
        )

        ml_confidence = _clamp(
            ml_result.get(
                "confidence",
                0.0,
            )
            if ml_available
            else 0.0
        )

        ml_is_buy = _is_ml_buy(
            ml_signal,
            ml_direction,
        )

        ml_is_sell = _is_ml_sell(
            ml_signal,
            ml_direction,
        )

        # ====================================================
        # Technical Components
        # ====================================================

        candle = _get_component(
            technical_result,
            "candle",
        )

        momentum = _get_component(
            technical_result,
            "momentum",
        )

        volume = _get_component(
            technical_result,
            "volume",
        )

        structure = _get_component(
            technical_result,
            "structure",
        )

        support_resistance = _get_component(
            technical_result,
            "support_resistance",
        )

        volatility = _get_component(
            technical_result,
            "volatility",
        )

        candle_signal = candle.get(
            "signal"
        )

        momentum_signal = momentum.get(
            "signal"
        )

        volume_signal = volume.get(
            "signal"
        )

        structure_signal = structure.get(
            "signal"
        )

        volatility_state = volatility.get(
            "volatility_state"
        )

        breakout = support_resistance.get(
            "breakout",
            False,
        )

        breakdown = support_resistance.get(
            "breakdown",
            False,
        )

        # ====================================================
        # Confidence / Agreement
        # ====================================================

        confidence_result = (
            _calculate_signal_confidence(
                technical_signal=technical_signal,
                technical_confidence=technical_confidence,
                ml_available=ml_available,
                ml_signal=ml_signal,
                ml_direction=ml_direction,
                ml_confidence=ml_confidence,
            )
        )

        final_confidence = (
            confidence_result["confidence"]
        )

        decision_mode = (
            confidence_result["mode"]
        )

        agreement = (
            confidence_result["agreement"]
        )

        conflict = (
            confidence_result["conflict"]
        )

        # ====================================================
        # Initial Final Signal
        # ====================================================

        reasons = []

        if conflict:

            final_signal = "WAIT"

            reasons.append(
                "Technical analysis and ML disagree."
            )

            reasons.append(
                "Wait for confirmation before entering."
            )

        elif technical_is_buy:

            final_signal = "BUY"

            reasons.append(
                "Technical analysis is bullish."
            )

        elif technical_is_sell:

            final_signal = "SELL"

            reasons.append(
                "Technical analysis is bearish."
            )

        else:

            final_signal = "WAIT"

            decision_mode = (
                "NO_CLEAR_TECHNICAL_SIGNAL"
            )

            reasons.append(
                "Technical analysis does not show "
                "a clear trade direction."
            )

        # ====================================================
        # ML Explanation
        # ====================================================

        if (
            ml_available
            and technical_is_buy
            and ml_is_buy
        ):

            reasons.append(
                "Technical analysis and ML "
                "both support BUY."
            )

        elif (
            ml_available
            and technical_is_sell
            and ml_is_sell
        ):

            reasons.append(
                "Technical analysis and ML "
                "both support SELL."
            )

        elif (
            ml_available
            and (
                technical_is_buy
                or technical_is_sell
            )
            and not conflict
        ):

            reasons.append(
                "ML is neutral and does not "
                "confirm the technical direction."
            )

        # ====================================================
        # WAIT Confidence Protection
        # ====================================================

        if final_signal == "WAIT":

            final_confidence = min(
                final_confidence,
                WAIT_MAX_CONFIDENCE,
            )

        final_confidence = round(
            _clamp(final_confidence),
            2,
        )

        # ====================================================
        # Technical Component Reasons
        # ====================================================

        _build_component_reasons(
            reasons=reasons,
            candle_signal=candle_signal,
            momentum_signal=momentum_signal,
            volume_signal=volume_signal,
            structure_signal=structure_signal,
            volatility_state=volatility_state,
            breakout=breakout,
            breakdown=breakdown,
            technical_is_buy=technical_is_buy,
            technical_is_sell=technical_is_sell,
        )

        # ====================================================
        # Risk Levels
        # ====================================================

        risk_signal = (
            final_signal
            if final_signal in (
                "BUY",
                "SELL",
            )
            else None
        )

        risk = _risk_levels(
            signal=risk_signal,
            entry=price,
            atr=atr,
            support_resistance=support_resistance,
        )

        holding = _holding_period_estimate(
            entry=risk.get("entry"),
            target1=risk.get("target1"),
            atr=atr,
        )

        # ====================================================
        # Risk / Reward Gate
        # ====================================================

        risk_reward = risk.get(
            "risk_reward"
        )

        if (
            final_signal in (
                "BUY",
                "SELL",
            )
            and risk_reward is not None
            and risk_reward < MIN_RISK_REWARD
        ):

            reasons.append(
                f"Trade rejected because "
                f"risk/reward is below "
                f"{MIN_RISK_REWARD:.1f}:1."
            )

            final_signal = "WAIT"

            decision_mode = (
                "POOR_RISK_REWARD"
            )

            final_confidence = min(
                final_confidence,
                WAIT_MAX_CONFIDENCE,
            )

            risk = {
                "entry": risk.get(
                    "entry"
                ),
                "stoploss": None,
                "target1": None,
                "target2": None,
                "risk_reward": risk_reward,
                "risk_percent": risk.get(
                    "risk_percent"
                ),
            }

            holding = None

        # ====================================================
        # Final Explanation
        # ====================================================

        if final_signal == "WAIT":

            if conflict:

                reasons.append(
                    "Final recommendation is WAIT "
                    "because technical and ML signals conflict."
                )

        elif final_signal == "BUY":

            reasons.append(
                "Bullish evidence is stronger "
                "than bearish evidence."
            )

        elif final_signal == "SELL":

            reasons.append(
                "Bearish evidence is stronger "
                "than bullish evidence."
            )

        # ====================================================
        # Return
        # ====================================================

        return {
            "available": True,

            # ------------------------------------------------
            # Final Decision
            # ------------------------------------------------

            "final_signal": final_signal,

            "final_confidence": final_confidence,

            "decision_mode": decision_mode,

            "agreement": agreement,

            "conflict": conflict,

            # ------------------------------------------------
            # Technical
            # ------------------------------------------------

            "technical_signal": technical_signal,

            "technical_strength": technical_strength,

            "technical_confidence": (
                technical_confidence
            ),

            # ------------------------------------------------
            # ML
            # ------------------------------------------------

            "ml_available": ml_available,

            "ml_signal": ml_signal,

            "ml_direction": ml_direction,

            "ml_confidence": ml_confidence,

            # ------------------------------------------------
            # Confidence Breakdown
            # ------------------------------------------------

            "confidence_breakdown": {
                "technical": {
                    "weight": TECH_WEIGHT,
                    "confidence": (
                        technical_confidence
                    ),
                    "signal": (
                        technical_signal
                    ),
                },

                "ml": {
                    "weight": ML_WEIGHT,
                    "confidence": ml_confidence,
                    "signal": ml_signal,
                    "direction": ml_direction,
                    "validation_accuracy": (
                        ml_result.get(
                            "validation_accuracy"
                        )
                        if ml_available
                        else None
                    ),
                },
            },

            # ------------------------------------------------
            # Trade Levels
            # ------------------------------------------------

            "entry": risk.get(
                "entry"
            ),

            "stoploss": risk.get(
                "stoploss"
            ),

            "target1": risk.get(
                "target1"
            ),

            "target2": risk.get(
                "target2"
            ),

            "risk_reward": risk.get(
                "risk_reward"
            ),

            "risk_percent": risk.get(
                "risk_percent"
            ),

            "holding_period": holding,

            # ------------------------------------------------
            # Explanation
            # ------------------------------------------------

            "reasons": reasons,
        }