import pandas as pd

from backend.features.feature_builder import FeatureBuilder


class SuperTrendStrategy:

    NAME = "SuperTrend Strategy"

    @staticmethod
    def analyze(df):

        df = FeatureBuilder.build(df)

        if len(df) < 50:

            return {
                "strategy": SuperTrendStrategy.NAME,
                "signal": "HOLD",
                "confidence": 0,
                "reason": ["Insufficient Data"]
            }

        multiplier = 3

        hl2 = (df["High"] + df["Low"]) / 2

        upperband = hl2 + multiplier * df["ATR"]

        lowerband = hl2 - multiplier * df["ATR"]

        trend = [True]

        supertrend = [lowerband.iloc[0]]

        for i in range(1, len(df)):

            if df["Close"].iloc[i] > upperband.iloc[i - 1]:

                trend.append(True)

            elif df["Close"].iloc[i] < lowerband.iloc[i - 1]:

                trend.append(False)

            else:

                trend.append(trend[-1])

            if trend[-1]:

                supertrend.append(lowerband.iloc[i])

            else:

                supertrend.append(upperband.iloc[i])

        df["SUPER_TREND"] = supertrend

        df["TREND"] = trend

        latest = df.iloc[-1]

        price = float(latest["Close"])

        atr = float(latest["ATR"])

        signal = "BUY" if latest["TREND"] else "SELL"

        confidence = 80

        reasons = []

        if latest["TREND"]:

            reasons.append("Price above SuperTrend")

        else:

            reasons.append("Price below SuperTrend")

        if latest["ADX"] > 25:

            confidence += 10

            reasons.append("Strong Trend")

        if latest["RSI"] > 60 and signal == "BUY":

            confidence += 5

            reasons.append("Bullish Momentum")

        if latest["RSI"] < 40 and signal == "SELL":

            confidence += 5

            reasons.append("Bearish Momentum")

        confidence = min(confidence, 95)

        if signal == "BUY":

            entry = price

            stoploss = price - (1.5 * atr)

            target1 = price + (2 * atr)

            target2 = price + (4 * atr)

        else:

            entry = price

            stoploss = price + (1.5 * atr)

            target1 = price - (2 * atr)

            target2 = price - (4 * atr)

        return {

            "strategy": SuperTrendStrategy.NAME,

            "signal": signal,

            "entry": round(entry,2),

            "stoploss": round(stoploss,2),

            "target1": round(target1,2),

            "target2": round(target2,2),

            "confidence": confidence,

            "risk_reward": 2.0,

            "supertrend": round(float(latest["SUPER_TREND"]),2),

            "reason": reasons

        }