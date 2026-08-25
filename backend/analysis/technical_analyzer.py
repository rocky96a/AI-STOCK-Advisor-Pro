from backend.analysis.candle_analyzer import CandleAnalyzer
from backend.analysis.trend_analyzer import TrendAnalyzer
from backend.analysis.momentum_analyzer import MomentumAnalyzer
from backend.analysis.volume_analyzer import VolumeAnalyzer
from backend.analysis.volatility_analyzer import VolatilityAnalyzer
from backend.analysis.structure_analyzer import StructureAnalyzer
from backend.features.indicators import Indicators
from backend.analysis.support_resistance_analyzer import(
    SupportResistanceAnalyzer
)
from backend.utils.trade_levels import compute as compute_trade_levels



class TechnicalAnalyzer:

    WEIGHTS = {
        "candle": 0.20,
        "trend": 0.20,
        "momentum": 0.15,
        "volume": 0.15,
        "structure": 0.15,
        "support_resistance": 0.10,
        "volatility": 0.05,
    }

    @staticmethod
    def _calculate_trade_levels(
        signal,
        price,
        atr,
        support_resistance,
    ):
        """
        Calculate practical entry, stop-loss and targets.

        These are technical estimates, NOT guaranteed future prices.
        """

        if price is None or atr is None:
            return {
                "entry": None,
                "stoploss": None,
                "target1": None,
                "target2": None,
                "risk_reward": None,
                "risk_percent": None,
            }

        if price <= 0 or atr <= 0:
            return {
                "entry": None,
                "stoploss": None,
                "target1": None,
                "target2": None,
                "risk_reward": None,
                "risk_percent": None,
            }

        entry = float(price)

        support = None
        resistance = None

        if isinstance(support_resistance, dict):

            nearest_support = support_resistance.get(
                "nearest_support"
            )

            nearest_resistance = support_resistance.get(
                "nearest_resistance"
            )

            if isinstance(nearest_support, dict):
                support = nearest_support.get("price")

            if isinstance(nearest_resistance, dict):
                resistance = nearest_resistance.get("price")

        # --------------------------------------------------
        # BUY
        # --------------------------------------------------

        if signal == "BUY":

            # Prefer nearby technical support.
            if support is not None and support < entry:
                stoploss = min(
                    support - atr * 0.25,
                    entry - atr * 1.0,
                )

            else:
                stoploss = entry - atr * 1.0

            risk = entry - stoploss

            if risk <= 0:
                return {
                    "entry": None,
                    "stoploss": None,
                    "target1": None,
                    "target2": None,
                    "risk_reward": None,
                    "risk_percent": None,
                }

            # First target = 1.5R
            target1 = entry + risk * 1.5

            # Second target = 2.5R
            target2 = entry + risk * 2.5

            # If resistance exists, do not blindly ignore it.
            if resistance is not None and resistance > entry:

                if resistance > entry:
                    target1 = min(
                        target1,
                        resistance,
                    )

            reward = target1 - entry

        # --------------------------------------------------
        # SELL
        # --------------------------------------------------

        elif signal == "SELL":

            # Prefer nearby technical resistance.
            if resistance is not None and resistance > entry:
                stoploss = max(
                    resistance + atr * 0.25,
                    entry + atr * 1.0,
                )

            else:
                stoploss = entry + atr * 1.0

            risk = stoploss - entry

            if risk <= 0:
                return {
                    "entry": None,
                    "stoploss": None,
                    "target1": None,
                    "target2": None,
                    "risk_reward": None,
                    "risk_percent": None,
                }

            # First target = 1.5R
            target1 = entry - risk * 1.5

            # Second target = 2.5R
            target2 = entry - risk * 2.5

            # Respect nearby support.
            if support is not None and support < entry:

                if support < entry:
                    target1 = max(
                        target1,
                        support,
                    )

            reward = entry - target1

        # --------------------------------------------------
        # HOLD
        # --------------------------------------------------

        else:

            return {
                "entry": entry,
                "stoploss": None,
                "target1": None,
                "target2": None,
                "risk_reward": None,
                "risk_percent": None,
            }

        if reward <= 0:
            risk_reward = None
        else:
            risk_reward = reward / risk

        risk_percent = (
            abs(risk) / entry
        ) * 100

        return {
            "entry": round(entry, 2),
            "stoploss": round(stoploss, 2),
            "target1": round(target1, 2),
            "target2": round(target2, 2),
            "risk_reward": (
                round(risk_reward, 2)
                if risk_reward is not None
                else None
            ),
            "risk_percent": round(
                risk_percent,
                2,
            ),
        }

    @staticmethod
    def analyze(df):

        if df is None or df.empty:
            return {
                "available": False,
                "reason": "No market data.",
            }

        # --------------------------------------------------
        # Calculate indicators
        # --------------------------------------------------

        try:
            df = Indicators.calculate(
                df.copy()
            )

        except Exception as exc:
            return {
                "available": False,
                "reason": (
                    f"Indicator calculation failed: {exc}"
                ),
            }

        # --------------------------------------------------
        # Run all technical analyzers
        # --------------------------------------------------

        components = {
            "candle": CandleAnalyzer.analyze(df),
            "trend": TrendAnalyzer.analyze(df),
            "momentum": MomentumAnalyzer.analyze(df),
            "volume": VolumeAnalyzer.analyze(df),
            "volatility": VolatilityAnalyzer.analyze(df),
            "structure": StructureAnalyzer.analyze(df),
            "support_resistance": (
                SupportResistanceAnalyzer.analyze(df)
            ),
        }

        bullish_total = 0.0
        bearish_total = 0.0

        bullish_components = 0
        bearish_components = 0
        neutral_components = 0

        component_summary = {}

        effective_weight_total = 0.0

        for name, analysis in components.items():

            if not isinstance(analysis, dict):
                continue

            if analysis.get("available") is False:
                continue

            bullish = float(
                analysis.get(
                    "bullish_score",
                    0.0,
                )
            )

            bearish = float(
                analysis.get(
                    "bearish_score",
                    0.0,
                )
            )

            signal = analysis.get("signal")
            strength = analysis.get("strength")

            base_weight = TechnicalAnalyzer.WEIGHTS.get(
                name,
                0.0,
            )

            if base_weight <= 0:
                continue

            effective_weight = base_weight

            # Strong signals receive more weight.
            if strength == "VERY_STRONG":
                effective_weight *= 1.25

            elif strength == "STRONG":
                effective_weight *= 1.15

            elif strength == "MODERATE":
                effective_weight *= 1.0

            elif strength == "WEAK":
                effective_weight *= 0.5

            bullish_contribution = (
                bullish * effective_weight
            )

            bearish_contribution = (
                bearish * effective_weight
            )

            bullish_total += bullish_contribution
            bearish_total += bearish_contribution

            effective_weight_total += effective_weight

            if signal in (
                "BUY",
                "BULLISH",
            ):
                bullish_components += 1

            elif signal in (
                "SELL",
                "BEARISH",
            ):
                bearish_components += 1

            else:
                neutral_components += 1

            component_summary[name] = {
                "signal": signal,
                "raw_signal": signal,
                "strength": strength,
                "base_weight": base_weight,
                "effective_weight": round(
                    effective_weight,
                    4,
                ),
                "bullish_score": round(
                    bullish,
                    2,
                ),
                "bearish_score": round(
                    bearish,
                    2,
                ),
                "bullish_contribution": round(
                    bullish_contribution,
                    2,
                ),
                "bearish_contribution": round(
                    bearish_contribution,
                    2,
                ),
            }

        if effective_weight_total > 0:

            bullish_score = (
                bullish_total
                / effective_weight_total
            )

            bearish_score = (
                bearish_total
                / effective_weight_total
            )

        else:

            bullish_score = 0.0
            bearish_score = 0.0

        score_difference = (
            bullish_score
            - bearish_score
        )

        # --------------------------------------------------
        # Final signal
        # --------------------------------------------------

        if score_difference >= 15:
            signal = "BUY"

        elif score_difference <= -15:
            signal = "SELL"

        else:
            signal = "HOLD"

        # --------------------------------------------------
        # Strength
        # --------------------------------------------------

        difference = abs(
            score_difference
        )

        if difference >= 30:
            strength = "VERY_STRONG"

        elif difference >= 20:
            strength = "STRONG"

        elif difference >= 10:
            strength = "MODERATE"

        else:
            strength = "WEAK"

        # --------------------------------------------------
        # Direction
        # --------------------------------------------------

        if signal == "BUY":
            direction = "UP"

        elif signal == "SELL":
            direction = "DOWN"

        else:
            direction = "SIDEWAYS"

        # --------------------------------------------------
        # Confidence
        # --------------------------------------------------

        total_score = (
            bullish_score
            + bearish_score
        )

        if total_score > 0:

            confidence = (
                max(
                    bullish_score,
                    bearish_score,
                )
                / total_score
            ) * 100

        else:
            confidence = 0.0

        # --------------------------------------------------
        # Reasons
        # --------------------------------------------------

        reasons = []

        if bearish_components > bullish_components:

            reasons.append(
                f"{bearish_components} technical "
                f"components are bearish"
            )

        elif bullish_components > bearish_components:

            reasons.append(
                f"{bullish_components} technical "
                f"components are bullish"
            )

        else:

            reasons.append(
                "Technical components are mixed"
            )

        candle = components.get(
            "candle",
            {},
        )

        if (
            candle.get("signal") == "BEARISH"
            and candle.get("strength") == "VERY_STRONG"
        ):

            reasons.append(
                "Strong bearish candlestick pressure"
            )

        elif (
            candle.get("signal") == "BULLISH"
            and candle.get("strength") == "VERY_STRONG"
        ):

            reasons.append(
                "Strong bullish candlestick pressure"
            )

        momentum = components.get(
            "momentum",
            {},
        )

        if momentum.get("signal") == "BEARISH":

            reasons.append(
                "Momentum is bearish"
            )

        elif momentum.get("signal") == "BULLISH":

            reasons.append(
                "Momentum is bullish"
            )

        volume = components.get(
            "volume",
            {},
        )

        if volume.get("signal") == "BEARISH":

            reasons.append(
                "Volume confirms bearish pressure"
            )

        elif volume.get("signal") == "BULLISH":

            reasons.append(
                "Volume confirms bullish pressure"
            )

        structure = components.get(
            "structure",
            {},
        )

        if structure.get("signal") == "BULLISH":

            reasons.append(
                "Market structure is bullish"
            )

        elif structure.get("signal") == "BEARISH":

            reasons.append(
                "Market structure is bearish"
            )

        volatility = components.get(
            "volatility",
            {},
        )

        if volatility.get(
            "volatility_state"
        ) == "HIGH":

            reasons.append(
                "Volatility state: HIGH"
            )

        support_resistance = components.get(
            "support_resistance",
            {},
        )

        if support_resistance.get(
            "breakout"
        ):

            reasons.append(
                "Resistance breakout detected"
            )

        if support_resistance.get(
            "breakdown"
        ):

            reasons.append(
                "Support breakdown detected"
            )

        if (
            bullish_components > 0
            and bearish_components > 0
        ):

            reasons.append(
                "Bullish and bearish technical "
                "signals are conflicting"
            )

        # --------------------------------------------------
        # Latest price / ATR
        # --------------------------------------------------

        price = None
        atr = None

        try:
            latest = df.iloc[-1]

            price = float(
                latest["Close"]
            )

        except (
            KeyError,
            TypeError,
            ValueError,
        ):
            price = None

        try:
            latest = df.iloc[-1]

            atr = float(
                latest["ATR"]
            )

        except (
            KeyError,
            TypeError,
            ValueError,
        ):
            atr = None

        # --------------------------------------------------
        # Trade levels
        # --------------------------------------------------

        # --------------------------------------------------
        # Trade levels
        # --------------------------------------------------

        supports = []
        resistances = []

        if isinstance(support_resistance, dict):
            supports = [
                float(x["price"])
                for x in support_resistance.get(
                    "support_levels",
                    [],
                )
                if isinstance(x, dict)
                and x.get("price") is not None
            ]

            resistances = [
                float(x["price"])
                for x in support_resistance.get(
                    "resistance_levels",
                    [],
                )
                if isinstance(x, dict)
                and x.get("price") is not None
            ]

        trade_levels = compute_trade_levels(
            signal=signal,
            price=price,
            atr=atr,
            resistances=resistances,
            supports=supports,
        )

        # --------------------------------------------------
        # Return
        # --------------------------------------------------

        return {
            "available": True,

            "signal": signal,

            "direction": direction,

            "strength": strength,

            "confidence": round(
                confidence,
                2,
            ),

            "bullish_score": round(
                bullish_score,
                2,
            ),

            "bearish_score": round(
                bearish_score,
                2,
            ),

            "score_difference": round(
                score_difference,
                2,
            ),

            "bullish_components": (
                bullish_components
            ),

            "bearish_components": (
                bearish_components
            ),

            "neutral_components": (
                neutral_components
            ),

            "analyzer_count": len(
                component_summary
            ),

            "weights": TechnicalAnalyzer.WEIGHTS,

            "reasons": reasons,

            "component_summary": (
                component_summary
            ),

            "components": components,

            "entry": trade_levels["entry"],

            "stoploss": trade_levels["stoploss"],

            "target1": trade_levels["target1"],

            "target2": trade_levels["target2"],

            "risk_reward": (
                trade_levels["risk_reward"]
            ),

            "risk_percent": (
                trade_levels["risk_percent"]
            ),
        }