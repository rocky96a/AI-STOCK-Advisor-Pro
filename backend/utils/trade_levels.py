"""
Turns a raw ATR distance into entry / stop-loss / target1 / target2
that respect actual support & resistance structure, instead of just
firing price +/- N*ATR blindly.

Rules of thumb encoded here (all standard, beginner-safe defaults):
  - Stop-loss sits just beyond the nearest S/R level that would
    invalidate the trade, but is clamped to 0.5x-2x ATR from entry
    so risk per trade never becomes silly-tight or silly-wide.
  - Target1 aims at the nearest resistance/support level (where
    price is statistically most likely to react), instead of
    projecting straight through a real chart wall.
  - Target2 aims at the next level after that, falling back to a
    plain ATR projection if no further structure is detected.
"""

MIN_ATR_MULT = 0.5   # tightest allowed stop distance
MAX_ATR_MULT = 2.0   # widest allowed stop distance
MIN_LEVEL_GAP_ATR = 0.4  # ignore an S/R level that's basically at entry


def _first_useful_level(levels, price, atr, above):
    """
    Pick the first level far enough from price to be a meaningful
    target/stop (skips levels that sit almost on top of the price).
    """
    for lvl in levels:
        gap = (lvl - price) if above else (price - lvl)
        if gap >= atr * MIN_LEVEL_GAP_ATR:
            return lvl
    return None


def compute(signal, price, atr, resistances, supports):
    """
    signal: one of "BUY", "STRONG BUY", "SELL", "STRONG SELL", "HOLD"
    resistances / supports: lists ordered nearest-to-price first
    """
    is_buy = signal in ("BUY", "STRONG BUY")
    is_sell = signal in ("SELL", "STRONG SELL")

    entry = round(price, 2)

    if not (is_buy or is_sell):
        # HOLD: no trade levels to project
        return {
            "entry": entry,
            "stoploss": None,
            "target1": None,
            "target2": None,
            "risk_reward": None,
            "risk_percent": None,
        }

    if is_buy:
        target_levels = resistances
        stop_levels = supports
    else:
        target_levels = supports
        stop_levels = resistances

    # ---------- Stop loss ----------
    raw_stop_dist = atr * 1.0
    structure_stop = _first_useful_level(stop_levels, price, atr, above=is_sell)

    if structure_stop is not None:
        stop_dist = abs(price - structure_stop) + atr * 0.25  # small buffer past the level
    else:
        stop_dist = raw_stop_dist

    stop_dist = max(atr * MIN_ATR_MULT, min(stop_dist, atr * MAX_ATR_MULT))
    stoploss = round(price - stop_dist, 2) if is_buy else round(price + stop_dist, 2)

    # ---------- Target 1 (nearest real structure, else 2x ATR) ----------
    t1_level = _first_useful_level(target_levels, price, atr, above=is_buy)
    raw_t1_dist = atr * 2.0

    if t1_level is not None:
        t1_dist = abs(t1_level - price)
        # if the wall is closer than 1x ATR, still give it room worth trading
        t1_dist = max(t1_dist, atr * 1.0)
    else:
        t1_dist = raw_t1_dist

    target1 = round(price + t1_dist, 2) if is_buy else round(price - t1_dist, 2)

    # ---------- Target 2 (next structure level beyond target1, else 3.5x ATR) ----------
    beyond_t1 = [
        lvl for lvl in target_levels
        if (lvl > target1 if is_buy else lvl < target1)
    ]
    t2_level = beyond_t1[0] if beyond_t1 else None
    raw_t2_dist = atr * 3.5

    if t2_level is not None:
        t2_dist = abs(t2_level - price)
    else:
        t2_dist = max(raw_t2_dist, t1_dist * 1.4)

    target2 = round(price + t2_dist, 2) if is_buy else round(price - t2_dist, 2)

    # ---------- Risk metrics ----------
    risk = abs(entry - stoploss)
    reward = abs(target1 - entry)
    risk_reward = round(reward / risk, 2) if risk > 0 else None
    risk_percent = round((risk / price) * 100, 2)

    return {
        "entry": entry,
        "stoploss": stoploss,
        "target1": target1,
        "target2": target2,
        "risk_reward": risk_reward,
        "risk_percent": risk_percent,
    }
