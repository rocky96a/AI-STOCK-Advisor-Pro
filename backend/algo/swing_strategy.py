from backend.features.feature_builder import FeatureBuilder


class SwingStrategy:

    NAME = "Swing Trading"

    @staticmethod
    def analyze(df):

        df = FeatureBuilder.build(df)

        if len(df) < 200:

            return {
                "strategy": SwingStrategy.NAME,
                "signal": "HOLD",
                "confidence": 0,
                "reason": ["Insufficient historical data"]
            }

        latest = df.iloc[-1]

        price = float(latest["Close"])

        atr = float(latest["ATR"])

        score = 0

        reasons = []

        # ==========================
        # Long-term Trend
        # ==========================

        if latest["EMA20"] > latest["EMA50"] > latest["EMA200"]:

            score += 3
            reasons.append("Strong EMA Uptrend")

        elif latest["EMA20"] < latest["EMA50"] < latest["EMA200"]:

            score -= 3
            reasons.append("Strong EMA Downtrend")

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

        if 55 <= latest["RSI"] <= 70:

            score += 2
            reasons.append("Bullish RSI")

        elif 30 <= latest["RSI"] <= 45:

            score -= 2
            reasons.append("Bearish RSI")

        # ==========================
        # ADX
        # ==========================

        if latest["ADX"] > 25:

            score += 1
            reasons.append("Strong Trend")

        # ==========================
        # Volume Confirmation
        # ==========================

        avg_volume = df["Volume"].tail(20).mean()

        if latest["Volume"] > avg_volume:

            score += 1
            reasons.append("Volume Confirmation")

        # ==========================
        # Signal
        # ==========================

        if score >= 6:

            signal = "BUY"

        elif score <= -6:

            signal = "SELL"

        else:

            signal = "HOLD"

        confidence = min(95, 50 + abs(score) * 6)

        # ==========================
        # Trade Levels
        # ==========================

        if signal == "BUY":

            entry = price

            stoploss = price - (2 * atr)

            target1 = price + (3 * atr)

            target2 = price + (6 * atr)

            rr = round((target1 - entry) / (entry - stoploss), 2)

        elif signal == "SELL":

            entry = price

            stoploss = price + (2 * atr)

            target1 = price - (3 * atr)

            target2 = price - (6 * atr)

            rr = round((entry - target1) / (stoploss - entry), 2)

        else:

            entry = price
            stoploss = None
            target1 = None
            target2 = None
            rr = None

        return {

            "strategy": SwingStrategy.NAME,

            "signal": signal,

            "confidence": confidence,

            "entry": round(entry,2),

            "stoploss": None if stoploss is None else round(stoploss,2),

            "target1": None if target1 is None else round(target1,2),

            "target2": None if target2 is None else round(target2,2),

            "risk_reward": rr,

            "holding_period": "5-20 Trading Days",

            "reason": reasons

        }