"""
Shared in-memory TTL cache.

Why this file exists
---------------------
Before this, YahooService.get_stock() hit yfinance (a network call, plus a
second slower `.info` call) EVERY time it was invoked - including from
inside loops like scanner_service.scan() (20 symbols) and app.py's
market bar route (13 tickers), on every single page load / refresh.
That is the direct cause of the app feeling slow: the same data was being
re-downloaded and re-parsed dozens of times a minute even though prices
only change every few seconds and don't need to be re-fetched on every
click.

This module is a tiny, dependency-free, thread-safe TTL (time-to-live)
cache that lives in process memory. The first request for a symbol pays
the network cost; every request after that, within the TTL window,
is served instantly from memory. When the TTL expires, the next request
refreshes it. No disk I/O, no external services required.

Usage
-----
    from backend.data.cache import cache_get, cache_set, cached

Manual:
    key = ("yahoo_stock", symbol, interval, period)
    hit = cache_get(key)
    if hit is None:
        hit = do_expensive_work()
        cache_set(key, hit, ttl=60)

Decorator:
    @cached(ttl=60)
    def expensive(symbol):
        ...
"""

import time
import threading
import functools

_LOCK = threading.RLock()
_STORE = {}  # key -> (expires_at_epoch_seconds, value)

DEFAULT_TTL = 60  # seconds

# Suggested TTLs by data type - tune here in one place instead of
# scattering magic numbers across the codebase.
TTL_INTRADAY = 20     # 1m/5m/15m candles - refresh often
TTL_DAILY = 90        # 1d/1wk/1mo candles - safe to hold longer
TTL_MARKET_BAR = 30   # index/global ticker strip
TTL_SCAN = 45         # top BUY/SELL scanner results
TTL_INFO = 300        # company info (sector/industry/marketcap) barely changes


def cache_get(key):
    """Return the cached value for key, or None if missing/expired."""
    with _LOCK:
        entry = _STORE.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if expires_at < time.time():
            _STORE.pop(key, None)
            return None
        return value


def cache_set(key, value, ttl=DEFAULT_TTL):
    """Store value under key for ttl seconds."""
    with _LOCK:
        _STORE[key] = (time.time() + ttl, value)
    return value


def cache_clear(prefix=None):
    """Clear the whole cache, or only keys whose tuple starts with prefix."""
    with _LOCK:
        if prefix is None:
            _STORE.clear()
            return
        dead = [k for k in _STORE if isinstance(k, tuple) and k[: len(prefix)] == tuple(prefix)]
        for k in dead:
            _STORE.pop(k, None)


def cache_stats():
    """Lightweight introspection endpoint-friendly summary."""
    with _LOCK:
        now = time.time()
        alive = sum(1 for exp, _ in _STORE.values() if exp >= now)
        return {
            "total_keys": len(_STORE),
            "alive_keys": alive,
            "expired_keys": len(_STORE) - alive,
        }


def cached(ttl=DEFAULT_TTL, key_fn=None):
    """
    Decorator that memoizes a function's return value in the shared cache.

    A None return value is never cached (so a failed fetch is retried on
    the next call rather than being "stuck" returning None for the TTL).
    """

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if key_fn:
                key = key_fn(*args, **kwargs)
            else:
                key = (fn.__module__, fn.__qualname__, args, tuple(sorted(kwargs.items())))

            hit = cache_get(key)
            if hit is not None:
                return hit

            result = fn(*args, **kwargs)

            if result is not None:
                cache_set(key, result, ttl=ttl)

            return result

        wrapper.cache_clear = lambda: cache_clear((fn.__module__, fn.__qualname__))
        return wrapper

    return decorator
