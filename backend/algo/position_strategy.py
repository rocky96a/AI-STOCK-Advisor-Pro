from backend.features.feature_builder import FeatureBuilder


class PositionStrategy:

    NAME = "Position Trading"

    @staticmethod
    def analyze(df):

        df = FeatureBuilder.build(df)

        if len(df) < 250:

            return {
                "strategy": PositionStrategy.NAME,
                "signal": "HOLD",
                "confidence": 0,
                "reason": ["Need at least 250 candles"]
            }

        latest = df.iloc[-1]

        price = float(latest["Close"])
        atr = float(latest["ATR"])

        score = 0
        reasons = []

        # ==========================
        # Long-Term EMA Trend
        # ==========================

        if latest["EMA50"] > latest["EMA200"]:

            score += 3
            reasons.append("EMA50 above EMA200")

        else:

            score -= 3
            reasons.append("EMA50 below EMA200")

        # ==========================
        # Price Trend
        # ==========================

        if price > latest["EMA200"]:

            score += 2
            reasons.append("Price above EMA200")

        else:

            score -= 2
            reasons.append("Price below EMA200")

        # ==========================
        # MACD
        # ==========================

        if latest["MACD"] > latest["MACD_SIGNAL"]:

            score += 2
            reasons.append("MACD Bullish")

        else:

            score -= 2
            reasons.append("MACD Bearish")

        # ==========================
        # RSI
        # ==========================

        if latest["RSI"] >= 55:

            score += 1
            reasons.append("RSI Strong")

        elif latest["RSI"] <= 45:

            score -= 1
            reasons.append("Weak RSI")

        # ==========================
        # ADX
        # ==========================

        if latest["ADX"] > 25:

            score += 1
            reasons.append("Strong Trend")

        # ==========================
        # Volume
        # ==========================

        avg_volume = df["Volume"].tail(30).mean()

        if latest["Volume"] > avg_volume:

            score += 1
            reasons.append("High Volume")

        # ==========================
        # Final Signal
        # ==========================

        if score >= 7:

            signal = "BUY"

        elif score <= -7:

            signal = "SELL"

        else:

            signal = "HOLD"

        confidence = min(95, 55 + abs(score) * 5)

        # ==========================
        # Trade Levels
        # ==========================

        if signal == "BUY":

            entry = price
            stoploss = price - (3 * atr)
            target1 = price + (5 * atr)
            target2 = price + (10 * atr)

            rr = round((target1-entry)/(entry-stoploss),2)

        elif signal == "SELL":

            entry = price
            stoploss = price + (3 * atr)
            target1 = price - (5 * atr)
            target2 = price - (10 * atr)

            rr = round((entry-target1)/(stoploss-entry),2)

        else:

            entry = price
            stoploss = None
            target1 = None
            target2 = None
            rr = None

        return {

            "strategy": PositionStrategy.NAME,

            "signal": signal,

            "confidence": confidence,

            "entry": round(entry,2),

            "stoploss": None if stoploss is None else round(stoploss,2),

            "target1": None if target1 is None else round(target1,2),

            "target2": None if target2 is None else round(target2,2),

            "risk_reward": rr,

            "holding_period": "1-6 Months",

            "reason": reasons

        }