from backend.algo.ema_strategy import EMAStrategy
from backend.algo.vwap_strategy import VWAPStrategy
from backend.algo.supertrend_strategy import SuperTrendStrategy
from backend.algo.bollinger_strategy import BollingerStrategy
from backend.algo.breakout_strategy import BreakoutStrategy
from backend.algo.orb_strategy import ORBStrategy
from backend.algo.scalping_strategy import ScalpingStrategy
from backend.algo.swing_strategy import SwingStrategy
from backend.algo.position_strategy import PositionStrategy


class StrategyManager:

    @staticmethod
    def analyze(df):

        strategies = []

        # Daily strategies
        strategies.append(EMAStrategy.analyze(df))
        strategies.append(SuperTrendStrategy.analyze(df))
        strategies.append(BollingerStrategy.analyze(df))
        strategies.append(BreakoutStrategy.analyze(df))
        strategies.append(SwingStrategy.analyze(df))
        strategies.append(PositionStrategy.analyze(df))

        buy = 0
        sell = 0
        hold = 0

        confidence = 0

        reasons = []

        entries = []
        stops = []
        targets = []

        for s in strategies:

            signal = s["signal"]

            confidence += s["confidence"]

            reasons.extend(s.get("reason", []))

            if s.get("entry") is not None:
                entries.append(s["entry"])

            if s.get("stoploss") is not None:
                stops.append(s["stoploss"])

            if s.get("target1") is not None:
                targets.append(s["target1"])

            if signal == "BUY":
                buy += 1

            elif signal == "SELL":
                sell += 1

            else:
                hold += 1

        avg_conf = round(confidence / len(strategies), 2)

        if buy > sell and buy >= 4:

            final_signal = "BUY"

        elif sell > buy and sell >= 4:

            final_signal = "SELL"

        else:

            final_signal = "HOLD"

        return {

            "signal": final_signal,

            "confidence": avg_conf,

            "buy_votes": buy,

            "sell_votes": sell,

            "hold_votes": hold,

            "entry": round(sum(entries)/len(entries),2) if entries else None,

            "stoploss": round(sum(stops)/len(stops),2) if stops else None,

            "target1": round(sum(targets)/len(targets),2) if targets else None,

            "strategies": strategies,

            "reason": list(set(reasons))

        }