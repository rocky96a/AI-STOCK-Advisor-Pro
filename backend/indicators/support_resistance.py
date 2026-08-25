"""
Support & Resistance detection.

Combines three classic techniques and merges them into a clean,
deduplicated set of levels around the current price:

  1. Swing highs / swing lows (price fractals / structure)
  2. Classic floor-trader pivot points (PP, R1-R3, S1-S3)
  3. Fibonacci retracement levels over the recent range

Returns the 3 nearest resistance levels above price and the 3
nearest support levels below price, ordered nearest-to-price first.
"""


def _find_swing_points(df, window=5):
    """
    A swing high is a candle whose High is greater than every candle
    `window` bars to its left AND right (same idea for swing lows).
    This is the standard "fractal" definition of market structure.
    """
    highs = df["High"].values
    lows = df["Low"].values
    n = len(df)

    swing_highs = []
    swing_lows = []

    for i in range(window, n - window):
        left_h = highs[i - window:i]
        right_h = highs[i + 1:i + window + 1]
        if highs[i] > left_h.max() and highs[i] > right_h.max():
            swing_highs.append(float(highs[i]))

        left_l = lows[i - window:i]
        right_l = lows[i + 1:i + window + 1]
        if lows[i] < left_l.min() and lows[i] < right_l.min():
            swing_lows.append(float(lows[i]))

    return swing_highs, swing_lows


def _classic_pivots(df):
    """
    Classic floor-trader pivots computed from the last fully closed
    candle. Works as "yesterday's" pivots regardless of timeframe.
    """
    last = df.iloc[-2] if len(df) > 1 else df.iloc[-1]

    h, l, c = float(last["High"]), float(last["Low"]), float(last["Close"])
    pp = (h + l + c) / 3

    return {
        "PP": pp,
        "R1": 2 * pp - l,
        "S1": 2 * pp - h,
        "R2": pp + (h - l),
        "S2": pp - (h - l),
        "R3": h + 2 * (pp - l),
        "S3": l - 2 * (h - pp),
    }


def _fibonacci_levels(df, lookback=90):
    """
    Fibonacci retracement levels between the swing high and swing
    low of the lookback window.
    """
    recent = df.tail(lookback)
    swing_high = float(recent["High"].max())
    swing_low = float(recent["Low"].min())
    diff = swing_high - swing_low

    if diff <= 0:
        return []

    ratios = [0.236, 0.382, 0.5, 0.618, 0.786]
    return [swing_high - diff * r for r in ratios]


def _cluster_levels(levels, price, tolerance=0.005):
    """
    Merge levels sitting within `tolerance` (fractional distance,
    default 0.5%) of each other into a single averaged level, so we
    don't show near-duplicate lines a few rupees apart.
    """
    if not levels:
        return []

    levels = sorted(levels)
    clusters = [[levels[0]]]

    for lvl in levels[1:]:
        if abs(lvl - clusters[-1][-1]) / price <= tolerance:
            clusters[-1].append(lvl)
        else:
            clusters.append([lvl])

    return [round(sum(c) / len(c), 2) for c in clusters]


def calculate(df, lookback=90, swing_window=5):
    price = float(df["Close"].iloc[-1])

    swing_highs, swing_lows = _find_swing_points(
        df.tail(lookback + swing_window), window=swing_window
    )
    pivots = _classic_pivots(df)
    fib_levels = _fibonacci_levels(df, lookback=lookback)

    candidate_levels = swing_highs + swing_lows + list(pivots.values()) + fib_levels
    clustered = _cluster_levels(candidate_levels, price)

    resistances = sorted(lvl for lvl in clustered if lvl > price)
    supports = sorted((lvl for lvl in clustered if lvl < price), reverse=True)

    # Fallback padding: on very short history there may not be 3 real
    # levels on each side. Pad with simple rolling high/low bands so
    # the UI/agent never has to handle a missing level.
    rolling_high = float(df["High"].tail(30).max())
    rolling_low = float(df["Low"].tail(30).min())

    while len(resistances) < 3:
        step = len(resistances) + 1
        resistances.append(round(max(rolling_high, price) * (1 + 0.01 * step), 2))

    while len(supports) < 3:
        step = len(supports) + 1
        supports.append(round(min(rolling_low, price) * (1 - 0.01 * step), 2))

    return {
        "resistance_1": resistances[0],
        "resistance_2": resistances[1],
        "resistance_3": resistances[2],
        "support_1": supports[0],
        "support_2": supports[1],
        "support_3": supports[2],
        # kept for backward compatibility with any existing callers
        "support": supports[0],
        "resistance": resistances[0],
        "pivots": {k: round(v, 2) for k, v in pivots.items()},
    }
