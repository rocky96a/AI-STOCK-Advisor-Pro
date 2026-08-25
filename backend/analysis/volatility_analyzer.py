import numpy as np
import pandas as pd


class VolatilityAnalyzer:

    @staticmethod
    def analyze(df):

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

        for column in required:
            work[column] = pd.to_numeric(
                work[column],
                errors="coerce",
            )

        work = work.dropna(
            subset=required
        ).reset_index(drop=True)

        if len(work) < 20:
            return {
                "available": False,
                "reason": "Not enough candles.",
            }

        # -----------------------------------------
        # True Range
        # -----------------------------------------

        previous_close = work["Close"].shift(1)

        tr1 = (
            work["High"]
            - work["Low"]
        )

        tr2 = (
            work["High"]
            - previous_close
        ).abs()

        tr3 = (
            work["Low"]
            - previous_close
        ).abs()

        work["TR"] = pd.concat(
            [tr1, tr2, tr3],
            axis=1,
        ).max(axis=1)

        # -----------------------------------------
        # ATR
        # -----------------------------------------

        atr = (
            work["TR"]
            .rolling(14)
            .mean()
        )

        current_atr = float(
            atr.iloc[-1]
        )

        # -----------------------------------------
        # ATR percentage
        # -----------------------------------------

        close = float(
            work["Close"].iloc[-1]
        )

        atr_percentage = (
            current_atr / close
        ) * 100 if close else 0

        # -----------------------------------------
        # Historical ATR comparison
        # -----------------------------------------

        atr_average = float(
            atr.iloc[-50:].mean()
        )

        if atr_average > 0:
            atr_ratio = (
                current_atr /
                atr_average
            )
        else:
            atr_ratio = 1.0

        # -----------------------------------------
        # Recent price range
        # -----------------------------------------

        recent_high = float(
            work["High"]
            .iloc[-20:]
            .max()
        )

        recent_low = float(
            work["Low"]
            .iloc[-20:]
            .min()
        )

        recent_range_percentage = (
            (recent_high - recent_low)
            / close
            * 100
        ) if close else 0

        # -----------------------------------------
        # Volatility state
        # -----------------------------------------

        if atr_ratio >= 1.5:
            volatility_state = "VERY_HIGH"

        elif atr_ratio >= 1.20:
            volatility_state = "HIGH"

        elif atr_ratio <= 0.75:
            volatility_state = "LOW"

        else:
            volatility_state = "NORMAL"

        # -----------------------------------------
        # Volatility direction
        # -----------------------------------------

        recent_atr = atr.iloc[-5:].mean()
        previous_atr = atr.iloc[-10:-5].mean()

        if recent_atr > previous_atr * 1.10:
            volatility_direction = "EXPANDING"

        elif recent_atr < previous_atr * 0.90:
            volatility_direction = "CONTRACTING"

        else:
            volatility_direction = "STABLE"

        # -----------------------------------------
        # Bullish / bearish scoring
        # -----------------------------------------

        bullish_score = 0.0
        bearish_score = 0.0
        reasons = []

        latest_open = float(
            work["Open"].iloc[-1]
        )

        latest_high = float(
            work["High"].iloc[-1]
        )

        latest_low = float(
            work["Low"].iloc[-1]
        )

        latest_close = float(
            work["Close"].iloc[-1]
        )

        latest_range = (
            latest_high - latest_low
        )

        # Strong downward candle + expanding volatility
        if (
            latest_close < latest_open
            and volatility_direction == "EXPANDING"
        ):
            bearish_score += 20
            reasons.append(
                "Bearish price movement "
                "with expanding volatility"
            )

        # Strong upward candle + expanding volatility
        elif (
            latest_close > latest_open
            and volatility_direction == "EXPANDING"
        ):
            bullish_score += 20
            reasons.append(
                "Bullish price movement "
                "with expanding volatility"
            )

        if volatility_state == "VERY_HIGH":
            reasons.append(
                "Very high volatility"
            )

        elif volatility_state == "HIGH":
            reasons.append(
                "High volatility"
            )

        elif volatility_state == "LOW":
            reasons.append(
                "Low volatility / compression"
            )

        # -----------------------------------------
        # Volatility breakout detection
        # -----------------------------------------

        breakout = False

        if len(work) >= 21:

            previous_high = float(
                work["High"]
                .iloc[-21:-1]
                .max()
            )

            previous_low = float(
                work["Low"]
                .iloc[-21:-1]
                .min()
            )

            if latest_close > previous_high:
                breakout = True
                bullish_score += 20
                reasons.append(
                    "Volatility breakout above "
                    "recent range"
                )

            elif latest_close < previous_low:
                breakout = True
                bearish_score += 20
                reasons.append(
                    "Volatility breakout below "
                    "recent range"
                )

        # -----------------------------------------
        # Final signal
        # -----------------------------------------

        if bullish_score > bearish_score:
            signal = "BULLISH"

        elif bearish_score > bullish_score:
            signal = "BEARISH"

        else:
            signal = "NEUTRAL"

        score_difference = abs(
            bullish_score - bearish_score
        )

        if score_difference >= 30:
            strength = "STRONG"

        elif score_difference >= 15:
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

            "atr": round(
                current_atr,
                2,
            ),

            "atr_percentage": round(
                atr_percentage,
                2,
            ),

            "average_atr": round(
                atr_average,
                2,
            ),

            "atr_ratio": round(
                atr_ratio,
                2,
            ),

            "volatility_state":
                volatility_state,

            "volatility_direction":
                volatility_direction,

            "recent_high": round(
                recent_high,
                2,
            ),

            "recent_low": round(
                recent_low,
                2,
            ),

            "recent_range_percentage":
                round(
                    recent_range_percentage,
                    2,
                ),

            "breakout": breakout,

            "reasons": reasons,
        }