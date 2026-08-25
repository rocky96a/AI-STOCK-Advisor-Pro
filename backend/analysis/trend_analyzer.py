import numpy as np
import pandas as pd


class TrendAnalyzer:

    @staticmethod
    def analyze(df):

        if df is None or df.empty:
            return {
                "available": False,
                "reason": "No market data.",
            }

        work = df.copy()

        required = [
            "Close",
            "EMA20",
            "EMA50",
            "EMA200",
            "ADX",
        ]

        missing = [
            col for col in required
            if col not in work.columns
        ]

        if missing:
            return {
                "available": False,
                "reason": f"Missing columns: {missing}",
            }

        work = (
            work
            .replace([np.inf, -np.inf], np.nan)
            .dropna(subset=required)
            .reset_index(drop=True)
        )

        if work.empty:
            return {
                "available": False,
                "reason": "No usable trend data.",
            }

        latest = work.iloc[-1]

        close = float(latest["Close"])
        ema20 = float(latest["EMA20"])
        ema50 = float(latest["EMA50"])
        ema200 = float(latest["EMA200"])
        adx = float(latest["ADX"])

        bullish_score = 0.0
        bearish_score = 0.0
        reasons = []

        # ------------------------------------------
        # Price vs moving averages
        # ------------------------------------------

        if close > ema20:
            bullish_score += 15
            reasons.append("Price above EMA20")
        else:
            bearish_score += 15
            reasons.append("Price below EMA20")

        if close > ema50:
            bullish_score += 15
            reasons.append("Price above EMA50")
        else:
            bearish_score += 15
            reasons.append("Price below EMA50")

        if close > ema200:
            bullish_score += 20
            reasons.append("Price above EMA200")
        else:
            bearish_score += 20
            reasons.append("Price below EMA200")

        # ------------------------------------------
        # EMA alignment
        # ------------------------------------------

        if ema20 > ema50 > ema200:
            bullish_score += 25
            reasons.append(
                "Bullish EMA alignment: EMA20 > EMA50 > EMA200"
            )

        elif ema20 < ema50 < ema200:
            bearish_score += 25
            reasons.append(
                "Bearish EMA alignment: EMA20 < EMA50 < EMA200"
            )

        else:
            reasons.append("EMA alignment mixed")

        # ------------------------------------------
        # EMA slopes
        # ------------------------------------------

        lookback = min(5, len(work) - 1)

        if lookback > 0:

            previous = work.iloc[-1 - lookback]

            ema20_change = (
                ema20 - float(previous["EMA20"])
            )

            ema50_change = (
                ema50 - float(previous["EMA50"])
            )

            if ema20_change > 0:
                bullish_score += 5
                reasons.append("EMA20 rising")
            elif ema20_change < 0:
                bearish_score += 5
                reasons.append("EMA20 falling")

            if ema50_change > 0:
                bullish_score += 5
                reasons.append("EMA50 rising")
            elif ema50_change < 0:
                bearish_score += 5
                reasons.append("EMA50 falling")

        # ------------------------------------------
        # ADX trend strength
        # ------------------------------------------

        if adx >= 25:
            trend_strength = "STRONG"
            reasons.append(
                f"ADX confirms strong trend ({adx:.2f})"
            )
        elif adx >= 20:
            trend_strength = "MODERATE"
            reasons.append(
                f"ADX shows developing trend ({adx:.2f})"
            )
        else:
            trend_strength = "WEAK"
            reasons.append(
                f"ADX shows weak trend ({adx:.2f})"
            )

        # ------------------------------------------
        # Final trend
        # ------------------------------------------

        if bullish_score > bearish_score + 10:
            signal = "BULLISH"

        elif bearish_score > bullish_score + 10:
            signal = "BEARISH"

        else:
            signal = "NEUTRAL"

        difference = abs(
            bullish_score - bearish_score
        )

        if difference >= 50:
            strength = "VERY_STRONG"
        elif difference >= 30:
            strength = "STRONG"
        elif difference >= 15:
            strength = "MODERATE"
        else:
            strength = "WEAK"

        # ------------------------------------------
        # Trend direction
        # ------------------------------------------

        if signal == "BULLISH":
            direction = "UP"
        elif signal == "BEARISH":
            direction = "DOWN"
        else:
            direction = "SIDEWAYS"

        return {
            "available": True,

            "signal": signal,

            "direction": direction,

            "strength": strength,

            "trend_strength": trend_strength,

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

            "ema20": round(
                ema20,
                2,
            ),

            "ema50": round(
                ema50,
                2,
            ),

            "ema200": round(
                ema200,
                2,
            ),

            "adx": round(
                adx,
                2,
            ),

            "reasons": reasons,
        }