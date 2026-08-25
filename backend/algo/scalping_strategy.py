import math

from backend.features.feature_builder import FeatureBuilder


class ScalpingStrategy:

    NAME = "Scalping Strategy"

    VALID_INTERVALS = ["1m", "2m", "5m"]

    @staticmethod
    def _hold(reason, confidence=0):

        return {
            "strategy": ScalpingStrategy.NAME,
            "signal": "HOLD",
            "entry": None,
            "stoploss": None,
            "target1": None,
            "target2": None,
            "confidence": confidence,
            "risk_reward": None,
            "reason": reason if isinstance(reason, list) else [reason],
        }

    @staticmethod
    def analyze(df, interval="5m"):

        # -----------------------------------
        # Validate interval
        # -----------------------------------

        if interval not in ScalpingStrategy.VALID_INTERVALS:

            return ScalpingStrategy._hold(
                f"Scalping supports only: "
                f"{', '.join(ScalpingStrategy.VALID_INTERVALS)}"
            )

        if df is None or len(df) < 60:

            return ScalpingStrategy._hold(
                "Insufficient intraday data"
            )

        # -----------------------------------
        # Build indicators/features
        # -----------------------------------

        try:
            df = FeatureBuilder.build(df.copy())
        except Exception as e:

            return ScalpingStrategy._hold(
                f"Feature calculation failed: {str(e)}"
            )

        required = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
            "EMA9",
            "EMA20",
            "RSI",
            "ATR",
        ]

        missing = [
            column
            for column in required
            if column not in df.columns
        ]

        if missing:

            return ScalpingStrategy._hold(
                f"Missing features: {missing}"
            )

        # -----------------------------------
        # Calculate VWAP if not available
        # -----------------------------------

        if "VWAP" not in df.columns:

            typical_price = (
                df["High"]
                + df["Low"]
                + df["Close"]
            ) / 3

            cumulative_volume = (
                df["Volume"]
                .replace(0, float("nan"))
                .cumsum()
            )

            df["VWAP"] = (
                (typical_price * df["Volume"]).cumsum()
                / cumulative_volume
            )

        # Remove invalid indicator rows

        df = df.dropna(
            subset=[
                "Open",
                "High",
                "Low",
                "Close",
                "Volume",
                "EMA9",
                "EMA20",
                "RSI",
                "ATR",
                "VWAP",
            ]
        )

        if len(df) < 20:

            return ScalpingStrategy._hold(
                "Insufficient valid indicator rows"
            )

        latest = df.iloc[-1]
        previous = df.iloc[-2]

        price = float(latest["Close"])
        atr = float(latest["ATR"])
        rsi = float(latest["RSI"])

        ema9 = float(latest["EMA9"])
        ema20 = float(latest["EMA20"])

        prev_ema9 = float(previous["EMA9"])
        prev_ema20 = float(previous["EMA20"])

        vwap = float(latest["VWAP"])

        volume = float(latest["Volume"])

        avg_volume = float(
            df["Volume"]
            .iloc[-21:-1]
            .mean()
        )

        avg_atr = float(
            df["ATR"]
            .iloc[-21:-1]
            .mean()
        )

        if (
            not math.isfinite(price)
            or not math.isfinite(atr)
            or atr <= 0
        ):

            return ScalpingStrategy._hold(
                "Invalid price or ATR"
            )

        # -----------------------------------
        # Scores
        # -----------------------------------

        bullish_score = 0
        bearish_score = 0

        bullish_reasons = []
        bearish_reasons = []

        # ===================================
        # 1. EMA 9 / EMA 20
        # ===================================

        bullish_cross = (
            prev_ema9 <= prev_ema20
            and ema9 > ema20
        )

        bearish_cross = (
            prev_ema9 >= prev_ema20
            and ema9 < ema20
        )

        if bullish_cross:

            bullish_score += 3
            bullish_reasons.append(
                "EMA9 crossed above EMA20"
            )

        elif ema9 > ema20:

            bullish_score += 1
            bullish_reasons.append(
                "EMA9 above EMA20"
            )

        if bearish_cross:

            bearish_score += 3
            bearish_reasons.append(
                "EMA9 crossed below EMA20"
            )

        elif ema9 < ema20:

            bearish_score += 1
            bearish_reasons.append(
                "EMA9 below EMA20"
            )

        # ===================================
        # 2. VWAP
        # ===================================

        if price > vwap:

            bullish_score += 2
            bullish_reasons.append(
                "Price above VWAP"
            )

        elif price < vwap:

            bearish_score += 2
            bearish_reasons.append(
                "Price below VWAP"
            )

        # ===================================
        # 3. RSI Momentum
        # ===================================

        if 52 <= rsi <= 70:

            bullish_score += 2
            bullish_reasons.append(
                "Bullish RSI momentum"
            )

        elif 30 <= rsi <= 48:

            bearish_score += 2
            bearish_reasons.append(
                "Bearish RSI momentum"
            )

        # Avoid chasing extreme RSI

        if rsi > 75:

            bullish_score -= 1
            bullish_reasons.append(
                "RSI overbought - chase risk"
            )

        elif rsi < 25:

            bearish_score -= 1
            bearish_reasons.append(
                "RSI oversold - reversal risk"
            )

        # ===================================
        # 4. Volume Surge
        # ===================================

        volume_ratio = 0

        if avg_volume > 0:

            volume_ratio = volume / avg_volume

        if volume_ratio >= 1.5:

            if price >= float(latest["Open"]):

                bullish_score += 2
                bullish_reasons.append(
                    "Strong bullish volume surge"
                )

            else:

                bearish_score += 2
                bearish_reasons.append(
                    "Strong bearish volume surge"
                )

        elif volume_ratio >= 1.2:

            if price >= float(latest["Open"]):

                bullish_score += 1
                bullish_reasons.append(
                    "Bullish volume confirmation"
                )

            else:

                bearish_score += 1
                bearish_reasons.append(
                    "Bearish volume confirmation"
                )

        # ===================================
        # 5. ATR / Volatility
        # ===================================

        if avg_atr > 0:

            atr_ratio = atr / avg_atr

        else:

            atr_ratio = 1.0

        if 1.0 <= atr_ratio <= 2.0:

            bullish_score += 1
            bearish_score += 1

        elif atr_ratio > 2.5:

            bullish_score -= 1
            bearish_score -= 1

        # ===================================
        # 6. Candle Momentum
        # ===================================

        candle_range = float(
            latest["High"] - latest["Low"]
        )

        candle_body = abs(
            float(latest["Close"])
            - float(latest["Open"])
        )

        body_ratio = (
            candle_body / candle_range
            if candle_range > 0
            else 0
        )

        if body_ratio >= 0.60:

            if price > float(latest["Open"]):

                bullish_score += 1
                bullish_reasons.append(
                    "Strong bullish candle"
                )

            elif price < float(latest["Open"]):

                bearish_score += 1
                bearish_reasons.append(
                    "Strong bearish candle"
                )

        # -----------------------------------
        # Final Signal
        # -----------------------------------

        minimum_score = 5
        minimum_edge = 2

        if (
            bullish_score >= minimum_score
            and bullish_score
            >= bearish_score + minimum_edge
        ):

            signal = "BUY"
            score = bullish_score
            reasons = bullish_reasons

        elif (
            bearish_score >= minimum_score
            and bearish_score
            >= bullish_score + minimum_edge
        ):

            signal = "SELL"
            score = bearish_score
            reasons = bearish_reasons

        else:

            signal = "HOLD"

            score = max(
                bullish_score,
                bearish_score
            )

            reasons = [
                "No high-quality scalping setup",
                f"Bullish score: {bullish_score}",
                f"Bearish score: {bearish_score}",
            ]

        # -----------------------------------
        # Confidence
        # -----------------------------------

        if signal == "HOLD":

            confidence = min(
                70,
                40 + score * 5
            )

        else:

            confidence = min(
                95,
                50 + score * 5
            )

        # -----------------------------------
        # Trade Levels
        # -----------------------------------

        entry = None
        stoploss = None
        target1 = None
        target2 = None
        risk_reward = None

        if signal == "BUY":

            entry = price

            stop_distance = max(
                atr * 0.8,
                price * 0.001
            )

            stoploss = entry - stop_distance

            risk = entry - stoploss

            target1 = entry + risk * 1.5
            target2 = entry + risk * 2.5

            risk_reward = 1.5

        elif signal == "SELL":

            entry = price

            stop_distance = max(
                atr * 0.8,
                price * 0.001
            )

            stoploss = entry + stop_distance

            risk = stoploss - entry

            target1 = entry - risk * 1.5
            target2 = entry - risk * 2.5

            risk_reward = 1.5

        # -----------------------------------
        # Response
        # -----------------------------------

        return {

            "strategy": ScalpingStrategy.NAME,

            "mode": "SCALPING",

            "interval": interval,

            "signal": signal,

            "entry": (
                round(entry, 2)
                if entry is not None
                else None
            ),

            "stoploss": (
                round(stoploss, 2)
                if stoploss is not None
                else None
            ),

            "target1": (
                round(target1, 2)
                if target1 is not None
                else None
            ),

            "target2": (
                round(target2, 2)
                if target2 is not None
                else None
            ),

            "confidence": round(
                float(confidence),
                2
            ),

            "risk_reward": risk_reward,

            "scores": {

                "bullish": bullish_score,

                "bearish": bearish_score,

            },

            "indicators": {

                "ema9": round(ema9, 2),

                "ema20": round(ema20, 2),

                "vwap": round(vwap, 2),

                "rsi": round(rsi, 2),

                "atr": round(atr, 2),

                "volume_ratio": round(
                    volume_ratio,
                    2
                ),

                "atr_ratio": round(
                    atr_ratio,
                    2
                ),

            },

            "reason": reasons,

        }