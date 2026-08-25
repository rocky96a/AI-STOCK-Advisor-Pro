import numpy as np
import pandas as pd


class RiskAnalyzer:

    @staticmethod
    def analyze(
        df,
        support_resistance=None,
        trend=None,
        momentum=None,
        candle=None,
        volume=None,
    ):
        """
        Human-style entry and risk/reward analysis.

        This does NOT place trades.
        It evaluates whether the current price offers
        a technically reasonable entry.
        """

        if df is None or df.empty:
            return {
                "available": False,
                "reason": "No market data.",
            }

        work = df.copy()

        required = [
            "Open",
            "High",
            "Low",
            "Close",
        ]

        missing = [
            column
            for column in required
            if column not in work.columns
        ]

        if missing:
            return {
                "available": False,
                "reason": f"Missing columns: {missing}",
            }

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
            return {
                "available": False,
                "reason": "No usable price data.",
            }

        latest = work.iloc[-1]

        price = float(latest["Close"])
        high = float(latest["High"])
        low = float(latest["Low"])

        # --------------------------------------------------
        # Support / resistance
        # --------------------------------------------------

        support = None
        resistance = None

        if support_resistance:
            nearest_support = (
                support_resistance.get(
                    "nearest_support"
                )
            )

            nearest_resistance = (
                support_resistance.get(
                    "nearest_resistance"
                )
            )

            if nearest_support:
                support = float(
                    nearest_support.get(
                        "price",
                        0,
                    )
                )

            if nearest_resistance:
                resistance = float(
                    nearest_resistance.get(
                        "price",
                        0,
                    )
                )

        # --------------------------------------------------
        # Fallback support / resistance
        # --------------------------------------------------

        if support is None or support <= 0:
            lookback = min(20, len(work))

            support = float(
                work["Low"]
                .tail(lookback)
                .min()
            )

        if resistance is None or resistance <= 0:
            lookback = min(20, len(work))

            resistance = float(
                work["High"]
                .tail(lookback)
                .max()
            )

        # --------------------------------------------------
        # Distances
        # --------------------------------------------------

        support_distance = (
            ((price - support) / price) * 100
            if price > 0
            else 0.0
        )

        resistance_distance = (
            ((resistance - price) / price) * 100
            if price > 0
            else 0.0
        )

        # --------------------------------------------------
        # ATR
        # --------------------------------------------------

        atr = None

        if "ATR" in latest.index:
            try:
                atr = float(latest["ATR"])
            except (TypeError, ValueError):
                atr = None

        if atr is None or not np.isfinite(atr) or atr <= 0:

            true_ranges = []

            previous_close = None

            for _, row in work.tail(20).iterrows():

                row_high = float(row["High"])
                row_low = float(row["Low"])

                if previous_close is None:

                    tr = row_high - row_low

                else:

                    tr = max(
                        row_high - row_low,
                        abs(
                            row_high
                            - previous_close
                        ),
                        abs(
                            row_low
                            - previous_close
                        ),
                    )

                true_ranges.append(tr)

                previous_close = float(
                    row["Close"]
                )

            if true_ranges:
                atr = float(
                    np.mean(true_ranges)
                )
            else:
                atr = price * 0.02

        # --------------------------------------------------
        # Market bias
        # --------------------------------------------------

        bullish_points = 0
        bearish_points = 0
        reasons = []

        def signal_of(component):
            if not component:
                return None

            return component.get(
                "signal"
            )

        candle_signal = signal_of(candle)
        trend_signal = signal_of(trend)
        momentum_signal = signal_of(momentum)
        volume_signal = signal_of(volume)

        # Candle
        if candle_signal == "BULLISH":
            bullish_points += 2

        elif candle_signal == "BEARISH":
            bearish_points += 2

        # Trend
        if trend_signal == "BULLISH":
            bullish_points += 2

        elif trend_signal == "BEARISH":
            bearish_points += 2

        # Momentum
        if momentum_signal == "BULLISH":
            bullish_points += 2

        elif momentum_signal == "BEARISH":
            bearish_points += 2

        # Volume
        if volume_signal == "BULLISH":
            bullish_points += 2

        elif volume_signal == "BEARISH":
            bearish_points += 2

        # --------------------------------------------------
        # Entry location
        # --------------------------------------------------

        near_support = (
            support_distance <= 2.0
        )

        near_resistance = (
            resistance_distance <= 2.0
        )

        breakout = False
        breakdown = False

        if price > resistance:
            breakout = True

        if price < support:
            breakdown = True

        # --------------------------------------------------
        # BUY setup
        # --------------------------------------------------

        buy_score = 0.0

        if near_support:
            buy_score += 20
            reasons.append(
                "Price is near support"
            )

        if trend_signal == "BULLISH":
            buy_score += 15
            reasons.append(
                "Trend supports BUY"
            )

        if momentum_signal == "BULLISH":
            buy_score += 15
            reasons.append(
                "Momentum supports BUY"
            )

        if candle_signal == "BULLISH":
            buy_score += 15
            reasons.append(
                "Candlestick pressure is bullish"
            )

        if volume_signal == "BULLISH":
            buy_score += 15
            reasons.append(
                "Volume confirms bullish pressure"
            )

        if breakout:
            buy_score += 20
            reasons.append(
                "Price is above resistance"
            )

        if near_resistance and not breakout:

            buy_score -= 25

            reasons.append(
                "Resistance is too close for a fresh BUY"
            )

        # --------------------------------------------------
        # SELL setup
        # --------------------------------------------------

        sell_score = 0.0

        if near_resistance:
            sell_score += 20
            reasons.append(
                "Price is near resistance"
            )

        if trend_signal == "BEARISH":
            sell_score += 15
            reasons.append(
                "Trend supports SELL"
            )

        if momentum_signal == "BEARISH":
            sell_score += 15
            reasons.append(
                "Momentum supports SELL"
            )

        if candle_signal == "BEARISH":
            sell_score += 15
            reasons.append(
                "Candlestick pressure is bearish"
            )

        if volume_signal == "BEARISH":
            sell_score += 15
            reasons.append(
                "Volume confirms bearish pressure"
            )

        if breakdown:
            sell_score += 20
            reasons.append(
                "Price is below support"
            )

        if near_support and not breakdown:

            sell_score -= 25

            reasons.append(
                "Support is too close for a fresh SELL"
            )

        # --------------------------------------------------
        # Risk / reward
        # --------------------------------------------------

        # Long setup:
        # stop below support using ATR protection.
        long_stop = min(
            support - (0.25 * atr),
            price - (0.75 * atr),
        )

        if long_stop <= 0:
            long_stop = price - atr

        long_target = resistance

        # If resistance is behind price, use ATR target.
        if long_target <= price:
            long_target = price + (
                1.5 * atr
            )

        long_risk = price - long_stop
        long_reward = long_target - price

        if long_risk > 0:
            long_rr = (
                long_reward / long_risk
            )
        else:
            long_rr = 0.0

        # Short setup:
        # stop above resistance.
        short_stop = max(
            resistance + (0.25 * atr),
            price + (0.75 * atr),
        )

        short_target = support

        if short_target >= price:
            short_target = price - (
                1.5 * atr
            )

        short_risk = short_stop - price
        short_reward = price - short_target

        if short_risk > 0:
            short_rr = (
                short_reward / short_risk
            )
        else:
            short_rr = 0.0

        # --------------------------------------------------
        # Risk/reward quality
        # --------------------------------------------------

        if long_rr >= 2:
            buy_score += 15
            reasons.append(
                "BUY risk/reward is favorable"
            )

        elif long_rr < 1:
            buy_score -= 15
            reasons.append(
                "BUY risk/reward is poor"
            )

        if short_rr >= 2:
            sell_score += 15
            reasons.append(
                "SELL risk/reward is favorable"
            )

        elif short_rr < 1:
            sell_score -= 15
            reasons.append(
                "SELL risk/reward is poor"
            )

        # --------------------------------------------------
        # Final entry quality
        # --------------------------------------------------

        if (
            buy_score > sell_score
            and buy_score >= 55
        ):
            entry_signal = "BUY"

        elif (
            sell_score > buy_score
            and sell_score >= 55
        ):
            entry_signal = "SELL"

        else:
            entry_signal = "WAIT"

        # --------------------------------------------------
        # Entry quality
        # --------------------------------------------------

        best_score = max(
            buy_score,
            sell_score,
        )

        if best_score >= 80:
            entry_quality = "EXCELLENT"

        elif best_score >= 65:
            entry_quality = "GOOD"

        elif best_score >= 50:
            entry_quality = "FAIR"

        else:
            entry_quality = "POOR"

        # --------------------------------------------------
        # Risk level
        # --------------------------------------------------

        if atr / price >= 0.05:
            risk_level = "HIGH"

        elif atr / price >= 0.025:
            risk_level = "MODERATE"

        else:
            risk_level = "LOW"

        # --------------------------------------------------
        # Clean duplicate reasons
        # --------------------------------------------------

        clean_reasons = []

        for reason in reasons:
            if reason not in clean_reasons:
                clean_reasons.append(reason)

        return {
            "available": True,

            "signal": entry_signal,

            "entry_quality": entry_quality,

            "risk_level": risk_level,

            "buy_score": round(
                max(0.0, buy_score),
                2,
            ),

            "sell_score": round(
                max(0.0, sell_score),
                2,
            ),

            "price": round(
                price,
                2,
            ),

            "atr": round(
                atr,
                2,
            ),

            "support": round(
                support,
                2,
            ),

            "resistance": round(
                resistance,
                2,
            ),

            "support_distance_percentage": round(
                support_distance,
                2,
            ),

            "resistance_distance_percentage": round(
                resistance_distance,
                2,
            ),

            "near_support": near_support,

            "near_resistance": near_resistance,

            "breakout": breakout,

            "breakdown": breakdown,

            "buy_setup": {
                "entry": round(
                    price,
                    2,
                ),
                "stop_loss": round(
                    long_stop,
                    2,
                ),
                "target": round(
                    long_target,
                    2,
                ),
                "risk": round(
                    long_risk,
                    2,
                ),
                "reward": round(
                    long_reward,
                    2,
                ),
                "risk_reward": round(
                    long_rr,
                    2,
                ),
            },

            "sell_setup": {
                "entry": round(
                    price,
                    2,
                ),
                "stop_loss": round(
                    short_stop,
                    2,
                ),
                "target": round(
                    short_target,
                    2,
                ),
                "risk": round(
                    short_risk,
                    2,
                ),
                "reward": round(
                    short_reward,
                    2,
                ),
                "risk_reward": round(
                    short_rr,
                    2,
                ),
            },

            "bullish_points": bullish_points,

            "bearish_points": bearish_points,

            "reasons": clean_reasons,
        }
