from backend.features.feature_builder import FeatureBuilder


class ORBStrategy:

    NAME = "Opening Range Breakout"

    @staticmethod
    def analyze(df, interval="5m", opening_minutes=15):

        df = FeatureBuilder.build(df)

        # -----------------------------------
        # ORB only supports intraday charts
        # -----------------------------------

        valid_intervals = [

            "1m",
            "2m",
            "5m",
            "15m",
            "30m"

        ]

        if interval not in valid_intervals:

            return {

                "strategy": ORBStrategy.NAME,

                "signal": "HOLD",

                "confidence": 0,

                "reason": [

                    "ORB only supports intraday intervals."

                ]

            }

        if len(df) < opening_minutes + 10:

            return {

                "strategy": ORBStrategy.NAME,

                "signal": "HOLD",

                "confidence": 0,

                "reason": [

                    "Insufficient intraday candles."

                ]

            }

        # -----------------------------------
        # Today's Session
        # -----------------------------------

        df = df.copy()

        try:
            df.index = df.index.tz_localize(None)
        except Exception:
            pass

        today = df.index[-1].date()

        today_df = df[df.index.date == today]

        if len(today_df) < opening_minutes:

            return {

                "strategy": ORBStrategy.NAME,

                "signal": "HOLD",

                "confidence": 0,

                "reason": [

                    "Today's session not complete."

                ]

            }

        # -----------------------------------
        # Opening Range
        # -----------------------------------

        opening = today_df.iloc[:opening_minutes]

        orb_high = float(opening["High"].max())

        orb_low = float(opening["Low"].min())

        latest = today_df.iloc[-1]

        price = float(latest["Close"])

        atr = float(latest["ATR"])

        volume = float(latest["Volume"])

        avg_volume = today_df["Volume"].mean()

        signal = "HOLD"

        confidence = 55

        reasons = []

        # -----------------------------------
        # Breakout
        # -----------------------------------

        if price > orb_high:

            signal = "BUY"

            confidence += 15

            reasons.append("Opening High Breakout")

        elif price < orb_low:

            signal = "SELL"

            confidence += 15

            reasons.append("Opening Low Breakdown")

        # -----------------------------------
        # Retest Confirmation
        # -----------------------------------

        if signal == "BUY":

            if latest["Low"] >= orb_high:

                confidence += 5

                reasons.append("Breakout Confirmed")

            else:

                confidence -= 10

                reasons.append("Retest Pending")

        elif signal == "SELL":

            if latest["High"] <= orb_low:

                confidence += 5

                reasons.append("Breakdown Confirmed")

            else:

                confidence -= 10

                reasons.append("Retest Pending")

        # -----------------------------------
        # Volume
        # -----------------------------------

        if volume > avg_volume:

            confidence += 10

            reasons.append("High Volume")

        # -----------------------------------
        # ATR
        # -----------------------------------

        if atr > today_df["ATR"].mean():

            confidence += 8

            reasons.append("ATR Expansion")

        # -----------------------------------
        # EMA Trend
        # -----------------------------------

        if signal == "BUY" and latest["EMA20"] > latest["EMA50"]:

            confidence += 7

            reasons.append("EMA Bullish")

        elif signal == "SELL" and latest["EMA20"] < latest["EMA50"]:

            confidence += 7

            reasons.append("EMA Bearish")

        # -----------------------------------
        # RSI
        # -----------------------------------

        if signal == "BUY" and latest["RSI"] > 55:

            confidence += 5

            reasons.append("RSI Bullish")

        elif signal == "SELL" and latest["RSI"] < 45:

            confidence += 5

            reasons.append("RSI Bearish")

        # -----------------------------------
        # Fake Breakout Filter
        # -----------------------------------

        body = abs(

            latest["Close"] -

            latest["Open"]

        )

        if body < atr * 0.25:

            confidence -= 15

            reasons.append("Weak Breakout Candle")

        confidence = max(0, min(confidence, 95))

        # -----------------------------------
        # Targets
        # -----------------------------------

        if signal == "BUY":

            entry = price

            stoploss = orb_low

            target1 = price + (2 * atr)

            target2 = price + (4 * atr)

        elif signal == "SELL":

            entry = price

            stoploss = orb_high

            target1 = price - (2 * atr)

            target2 = price - (4 * atr)

        else:

            entry = price

            stoploss = None

            target1 = None

            target2 = None

        if stoploss is not None:

            risk = abs(entry - stoploss)

            reward = abs(target1 - entry)

            rr = round(reward / risk, 2) if risk else None

        else:

            rr = None

        return {

            "strategy": ORBStrategy.NAME,

            "signal": signal,

            "entry": round(entry, 2),

            "stoploss": None if stoploss is None else round(stoploss, 2),

            "target1": None if target1 is None else round(target1, 2),

            "target2": None if target2 is None else round(target2, 2),

            "confidence": confidence,

            "risk_reward": rr,

            "opening_high": round(orb_high, 2),

            "opening_low": round(orb_low, 2),

            "reason": reasons

        }