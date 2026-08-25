from backend.features.feature_builder import FeatureBuilder


class BreakoutStrategy:

    NAME = "Breakout & Retest"

    @staticmethod
    def analyze(df):

        df = FeatureBuilder.build(df)

        if len(df) < 60:

            return {

                "strategy": BreakoutStrategy.NAME,

                "signal": "HOLD",

                "confidence": 0,

                "reason": [

                    "Insufficient Data"

                ]

            }

        latest = df.iloc[-1]

        previous = df.iloc[-2]

        price = float(latest["Close"])

        atr = float(latest["ATR"])

        volume = float(latest["Volume"])

        avg_volume = df["Volume"].tail(20).mean()

        swing_high = df["High"].tail(20).max()

        swing_low = df["Low"].tail(20).min()

        confidence = 55

        signal = "HOLD"

        reasons = []

        # --------------------
        # Breakout
        # --------------------

        if (

            previous["Close"] <= swing_high

            and

            price > swing_high

        ):

            signal = "BUY"

            confidence += 20

            reasons.append("Resistance Breakout")

        elif (

            previous["Close"] >= swing_low

            and

            price < swing_low

        ):

            signal = "SELL"

            confidence += 20

            reasons.append("Support Breakdown")

        # --------------------
        # Retest
        # --------------------

        if signal == "BUY":

            if latest["Low"] >= swing_high:

                confidence += 8

                reasons.append("Retest Confirmed")

            else:

                confidence -= 10

                reasons.append("Retest Pending")

        elif signal == "SELL":

            if latest["High"] <= swing_low:

                confidence += 8

                reasons.append("Retest Confirmed")

            else:

                confidence -= 10

                reasons.append("Retest Pending")

        # --------------------
        # Volume
        # --------------------

        if volume > avg_volume * 1.2:

            confidence += 10

            reasons.append("Volume Spike")

        # --------------------
        # ATR
        # --------------------

        if atr > df["ATR"].tail(20).mean():

            confidence += 8

            reasons.append("ATR Expansion")

        # --------------------
        # EMA Filter
        # --------------------

        if signal == "BUY":

            if latest["EMA20"] > latest["EMA50"]:

                confidence += 7

                reasons.append("Bullish EMA")

        elif signal == "SELL":

            if latest["EMA20"] < latest["EMA50"]:

                confidence += 7

                reasons.append("Bearish EMA")

        # --------------------
        # RSI
        # --------------------

        if signal == "BUY":

            if latest["RSI"] > 55:

                confidence += 5

                reasons.append("Bullish RSI")

        elif signal == "SELL":

            if latest["RSI"] < 45:

                confidence += 5

                reasons.append("Bearish RSI")

        # --------------------
        # Fake Breakout Filter
        # --------------------

        body = abs(

            latest["Close"] -

            latest["Open"]

        )

        if body < atr * 0.30:

            confidence -= 15

            reasons.append("Weak Candle")

        confidence = max(

            0,

            min(confidence,95)

        )

        # --------------------
        # Targets
        # --------------------

        if signal == "BUY":

            entry = price

            stoploss = swing_high

            target1 = entry + (2 * atr)

            target2 = entry + (4 * atr)

        elif signal == "SELL":

            entry = price

            stoploss = swing_low

            target1 = entry - (2 * atr)

            target2 = entry - (4 * atr)

        else:

            entry = price

            stoploss = None

            target1 = None

            target2 = None

        if stoploss is not None:

            risk = abs(entry-stoploss)

            reward = abs(target1-entry)

            rr = round(reward/risk,2) if risk else None

        else:

            rr = None

        return {

            "strategy": BreakoutStrategy.NAME,

            "signal": signal,

            "entry": round(entry,2),

            "stoploss": None if stoploss is None else round(stoploss,2),

            "target1": None if target1 is None else round(target1,2),

            "target2": None if target2 is None else round(target2,2),

            "confidence": confidence,

            "risk_reward": rr,

            "swing_high": round(float(swing_high),2),

            "swing_low": round(float(swing_low),2),

            "reason": reasons

        }