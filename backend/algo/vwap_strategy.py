from backend.features.feature_builder import FeatureBuilder


class VWAPStrategy:

    NAME = "VWAP Strategy"

    @staticmethod
    def analyze(df):

        df = FeatureBuilder.build(df)

        if len(df) < 30:

            return {
                "strategy": VWAPStrategy.NAME,
                "signal": "HOLD",
                "confidence": 0,
                "reason": ["Insufficient data"]
            }

        latest = df.iloc[-1]

        price = float(latest["Close"])
        high = float(latest["High"])
        low = float(latest["Low"])

        volume = float(latest["Volume"])
        avg_volume = df["Volume"].tail(20).mean()

        atr = float(latest["ATR"])

        # -----------------------------
        # VWAP Calculation
        # -----------------------------

        typical_price = (df["High"] + df["Low"] + df["Close"]) / 3

        cumulative_tp_vol = (typical_price * df["Volume"]).cumsum()

        cumulative_vol = df["Volume"].cumsum()

        df["VWAP"] = cumulative_tp_vol / cumulative_vol

        vwap = float(df.iloc[-1]["VWAP"])

        signal = "HOLD"

        confidence = 50

        reasons = []

        # -----------------------------
        # BUY
        # -----------------------------

        if price > vwap:

            signal = "BUY"

            confidence += 20

            reasons.append("Price above VWAP")

            if volume > avg_volume:

                confidence += 10

                reasons.append("Strong buying volume")

        # -----------------------------
        # SELL
        # -----------------------------

        elif price < vwap:

            signal = "SELL"

            confidence += 20

            reasons.append("Price below VWAP")

            if volume > avg_volume:

                confidence += 10

                reasons.append("Strong selling volume")

        confidence = min(confidence, 95)

        # -----------------------------
        # Trade Levels
        # -----------------------------

        if signal == "BUY":

            entry = price

            stoploss = price - (1.5 * atr)

            target1 = price + (2 * atr)

            target2 = price + (4 * atr)

        elif signal == "SELL":

            entry = price

            stoploss = price + (1.5 * atr)

            target1 = price - (2 * atr)

            target2 = price - (4 * atr)

        else:

            entry = price

            stoploss = None

            target1 = None

            target2 = None

        return {

            "strategy": VWAPStrategy.NAME,

            "signal": signal,

            "entry": round(entry,2),

            "stoploss": None if stoploss is None else round(stoploss,2),

            "target1": None if target1 is None else round(target1,2),

            "target2": None if target2 is None else round(target2,2),

            "risk_reward": 2.0 if signal != "HOLD" else None,

            "confidence": confidence,

            "vwap": round(vwap,2),

            "reason": reasons

        }