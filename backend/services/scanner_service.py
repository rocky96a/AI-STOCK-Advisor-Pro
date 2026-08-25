"""
Market Scanner — runs the TechnicalAgent across a list of symbols
and ranks them by a composite "safety score": high confidence,
healthy risk:reward, and low risk% (small stop distance relative to
price). This directly answers "what's safe today with good
profit potential and low loss risk".

ML is intentionally NOT run for every symbol here — training a
Random Forest per stock is a few seconds each, and across 50 stocks
that adds up to minutes. Use `enrich_with_ml=True` only on the
shortlist (top N) that come back from the fast technical pass.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

from backend.services.yahoo_service import YahooService
from backend.agents.technical_agent import TechnicalAgent
from backend.ml.ml_agent import MLAgent
from backend.data.cache import cache_get, cache_set, TTL_SCAN
from backend.data.indian_stock_universe import get_indian_stocks

# How many symbols to fetch from Yahoo Finance in parallel on a cold
# scan. This is I/O-bound (network requests), so threads help a lot
# here even though Python has a GIL — most of the wait time is spent
# blocked on the network, not on the CPU.
SCAN_WORKERS = 10


# The full Nifty-50-ish large-cap universe (backend/data/indian_stock_universe.py)
# instead of a hardcoded 20-symbol subset. More candidates scanned = a
# real top-10 BUY and top-10 SELL list instead of "BUY 2 / SELL 5"
# because there simply weren't enough symbols in the pool to fill 10
# qualifying slots on each side.
DEFAULT_WATCHLIST = get_indian_stocks()


def _safety_score(analysis):
    """
    Higher is safer + more attractive.
      + confidence (0-95)
      + risk_reward, capped so a wild 10:1 outlier doesn't dominate
      - risk_percent (smaller stop distance = safer position sizing)
    Only meaningful for BUY/SELL signals with real trade levels.
    """
    if analysis["signal"] not in ("BUY", "STRONG BUY", "SELL", "STRONG SELL"):
        return None

    if analysis.get("risk_reward") is None or analysis.get("risk_percent") is None:
        return None

    rr = min(analysis["risk_reward"], 4.0)  # cap outliers
    risk_pct = max(analysis["risk_percent"], 0.1)  # avoid div by ~0

    score = (analysis["confidence"] * 0.5) + (rr * 10) - (risk_pct * 5)
    return round(score, 2)


def _fetch_and_score(symbol):
    """Load one symbol and score it. Returns (score, entry, df) or None.
    Isolated into its own function so it can run inside a thread pool —
    each call is dominated by network wait time (or a cache hit), so
    running several symbols concurrently instead of one-by-one is a
    big win on a cold cache.
    """
    stock = YahooService.get_stock(symbol)
    if stock is None:
        return None

    try:
        analysis = TechnicalAgent.analyze(stock["df"])
    except Exception:
        # Skip symbols with insufficient/bad data rather than
        # crashing the whole scan.
        return None

    score = _safety_score(analysis)
    if score is None:
        return None  # skip HOLDs and anything without valid trade levels

    entry = {
        "symbol": symbol,
        "company": stock["company"],
        "price": stock["price"],
        "signal": analysis["signal"],
        "confidence": analysis["confidence"],
        "entry": analysis["entry"],
        "stoploss": analysis["stoploss"],
        "target1": analysis["target1"],
        "target2": analysis["target2"],
        "risk_reward": analysis["risk_reward"],
        "risk_percent": analysis["risk_percent"],
        "safety_score": score,
    }

    return (score, entry, stock["df"])


def _scan_all(symbols=None):
    """
    Run the technical agent across every symbol in the watchlist ONCE and
    return every scored BUY/SELL entry (unsorted-by-type, unsplit).

    This is cached for TTL_SCAN seconds so that repeated calls (e.g. the
    dashboard's watchlist panel AND the Top Picks panel both wanting a
    scan within the same few seconds) reuse one pass instead of
    re-running the technical agent across the whole watchlist twice.

    On a cold cache, symbols are fetched concurrently (SCAN_WORKERS at a
    time) since each fetch is mostly spent waiting on the network —
    a 20-symbol scan that used to take ~20x a single fetch now takes
    roughly (20 / SCAN_WORKERS)x instead.
    """
    symbols = symbols or DEFAULT_WATCHLIST

    cache_key = ("scan_all", tuple(symbols))
    cached_results = cache_get(cache_key)
    if cached_results is not None:
        return cached_results

    results = []

    with ThreadPoolExecutor(max_workers=SCAN_WORKERS) as pool:
        futures = {pool.submit(_fetch_and_score, symbol): symbol for symbol in symbols}

        for future in as_completed(futures):
            try:
                outcome = future.result()
            except Exception as exc:
                print(f"[Scanner] {futures[future]} failed: {exc}")
                continue

            if outcome is not None:
                results.append(outcome)

    cache_set(cache_key, results, ttl=TTL_SCAN)
    return results


def scan(symbols=None, top_n=10, enrich_with_ml=False):
    """Top N entries overall (BUY and SELL mixed), highest safety score first."""
    results = _scan_all(symbols)

    ranked = sorted(results, key=lambda r: r[0], reverse=True)
    top = ranked[:top_n]

    if enrich_with_ml:
        for _, entry, df in top:
            ml_result = MLAgent.predict(df)
            entry["ml"] = ml_result if ml_result.get("available") else {"available": False}

    return [entry for _, entry, _ in top]


def scan_recommendations(symbols=None, buy_n=10, sell_n=10, enrich_with_ml=False):
    """
    Today's actionable picks, split into a BUY list and a SELL list —
    each ranked by safety score (confidence + risk:reward - risk%).

    Returns:
        {
            "buy": [ {symbol, company, price, signal, confidence,
                       entry, stoploss, target1, target2,
                       risk_reward, risk_percent, safety_score}, ... ],
            "sell": [ ... same shape ... ],
            "generated_at": ISO timestamp,
        }
    """
    import datetime

    results = _scan_all(symbols)

    buy_signals = {"BUY", "STRONG BUY"}
    sell_signals = {"SELL", "STRONG SELL"}

    buys = sorted(
        (r for r in results if r[1]["signal"] in buy_signals),
        key=lambda r: r[0],
        reverse=True,
    )[:buy_n]

    sells = sorted(
        (r for r in results if r[1]["signal"] in sell_signals),
        key=lambda r: r[0],
        reverse=True,
    )[:sell_n]

    if enrich_with_ml:
        for _, entry, df in buys + sells:
            ml_result = MLAgent.predict(df)
            entry["ml"] = ml_result if ml_result.get("available") else {"available": False}

    return {
        "buy": [entry for _, entry, _ in buys],
        "sell": [entry for _, entry, _ in sells],
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }
