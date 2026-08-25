from backend.features.feature_builder import FeatureBuilder


class EMAStrategy:

    NAME = "EMA Crossover"

    @staticmethod
    def analyze(df):

        # Build indicators
        df = FeatureBuilder.build(df)

        if len(df) < 60:
            return {
                "strategy": EMAStrategy.NAME,
                "signal": "HOLD",
                "confidence": 0,
                "reason": ["Not enough historical data"]
            }

        latest = df.iloc[-1]
        previous = df.iloc[-2]

        ema20 = latest["EMA20"]
        ema50 = latest["EMA50"]

        prev20 = previous["EMA20"]
        prev50 = previous["EMA50"]

        price = float(latest["Close"])
        atr = float(latest["ATR"])

        signal = "HOLD"
        confidence = 50
        reasons = []

        # --------------------------
        # BUY CROSS
        # --------------------------

        if prev20 < prev50 and ema20 > ema50:

            signal = "BUY"
            confidence = 88

            reasons.append("EMA20 crossed above EMA50")
            reasons.append("Bullish trend started")

        # --------------------------
        # SELL CROSS
        # --------------------------

        elif prev20 > prev50 and ema20 < ema50:

            signal = "SELL"
            confidence = 88

            reasons.append("EMA20 crossed below EMA50")
            reasons.append("Bearish trend started")

        else:

            if ema20 > ema50:
                reasons.append("Bullish trend continues")

            elif ema20 < ema50:
                reasons.append("Bearish trend continues")

            signal = "HOLD"
            confidence = 60

        # --------------------------
        # Targets
        # --------------------------

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

            "strategy": EMAStrategy.NAME,

            "signal": signal,

            "entry": round(entry,2),

            "stoploss": None if stoploss is None else round(stoploss,2),

            "target1": None if target1 is None else round(target1,2),

            "target2": None if target2 is None else round(target2,2),

            "confidence": confidence,

            "risk_reward": 2.0 if signal != "HOLD" else None,

            "reason": reasons

        }