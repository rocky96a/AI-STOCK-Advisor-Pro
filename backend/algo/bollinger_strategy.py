import numpy as np

from backend.features.feature_builder import FeatureBuilder


class BollingerStrategy:

    NAME = "Bollinger Breakout"

    @staticmethod
    def analyze(df):

        df = FeatureBuilder.build(df)

        if len(df) < 40:

            return {
                "strategy": BollingerStrategy.NAME,
                "signal": "HOLD",
                "confidence": 0,
                "reason": ["Insufficient data"]
            }

        # -----------------------------
        # Bollinger Bands
        # -----------------------------

        df["BB_MIDDLE"] = df["Close"].rolling(20).mean()

        std = df["Close"].rolling(20).std()

        df["BB_UPPER"] = df["BB_MIDDLE"] + (2 * std)

        df["BB_LOWER"] = df["BB_MIDDLE"] - (2 * std)

        df["BB_WIDTH"] = (
            (df["BB_UPPER"] - df["BB_LOWER"])
            / df["BB_MIDDLE"]
        )

        latest = df.iloc[-1]
        previous = df.iloc[-2]

        price = float(latest["Close"])
        atr = float(latest["ATR"])

        volume = float(latest["Volume"])
        avg_volume = df["Volume"].tail(20).mean()

        upper = float(latest["BB_UPPER"])
        lower = float(latest["BB_LOWER"])
        middle = float(latest["BB_MIDDLE"])

        confidence = 55
        reasons = []

        signal = "HOLD"

        # -----------------------------
        # Detect Squeeze
        # -----------------------------

        recent_width = df["BB_WIDTH"].tail(20)

        squeeze = latest["BB_WIDTH"] <= recent_width.quantile(0.20)

        if squeeze:

            confidence += 10
            reasons.append("Bollinger Squeeze")

        # -----------------------------
        # BUY Breakout
        # -----------------------------

        if (

            previous["Close"] <= previous["BB_UPPER"]

            and

            price > upper

        ):

            signal = "BUY"

            confidence += 15

            reasons.append("Upper Band Breakout")

        # -----------------------------
        # SELL Breakdown
        # -----------------------------

        elif (

            previous["Close"] >= previous["BB_LOWER"]

            and

            price < lower

        ):

            signal = "SELL"

            confidence += 15

            reasons.append("Lower Band Breakdown")

        # -----------------------------
        # Fake Breakout Filter
        # -----------------------------

        candle_body = abs(latest["Close"] - latest["Open"])

        if candle_body < (atr * 0.30):

            confidence -= 15

            reasons.append("Weak candle body")

        # -----------------------------
        # ATR Confirmation
        # -----------------------------

        if atr > df["ATR"].tail(20).mean():

            confidence += 8

            reasons.append("ATR Expansion")

        # -----------------------------
        # Volume Confirmation
        # -----------------------------

        if volume > avg_volume:

            confidence += 10

            reasons.append("High Volume")

        # -----------------------------
        # RSI Confirmation
        # -----------------------------

        if signal == "BUY" and latest["RSI"] > 55:

            confidence += 7

            reasons.append("RSI Bullish")

        if signal == "SELL" and latest["RSI"] < 45:

            confidence += 7

            reasons.append("RSI Bearish")

        confidence = max(0, min(confidence, 95))

        # -----------------------------
        # Trade Levels
        # -----------------------------

        if signal == "BUY":

            entry = price

            stoploss = middle

            target1 = price + (2 * atr)

            target2 = price + (4 * atr)

        elif signal == "SELL":

            entry = price

            stoploss = middle

            target1 = price - (2 * atr)

            target2 = price - (4 * atr)

        else:

            entry = price

            stoploss = None

            target1 = None

            target2 = None

        return {

            "strategy": BollingerStrategy.NAME,

            "signal": signal,

            "entry": round(entry,2),

            "stoploss": None if stoploss is None else round(stoploss,2),

            "target1": None if target1 is None else round(target1,2),

            "target2": None if target2 is None else round(target2,2),

            "confidence": confidence,

            "risk_reward": 2.0 if signal != "HOLD" else None,

            "bollinger": {

                "upper": round(upper,2),

                "middle": round(middle,2),

                "lower": round(lower,2),

                "width": round(float(latest["BB_WIDTH"]),4)

            },

            "reason": reasons

        }