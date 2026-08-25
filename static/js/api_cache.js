/* =====================================================
   API RESPONSE CACHE (client-side)

   Problem this solves
   --------------------
   This is a multi-page app (index / watchlist / portfolio are separate
   Flask templates, not a single-page app), so every time you navigate
   from the dashboard to another page and back, the browser does a full
   page reload — which re-ran /api/predict and /api/chart from scratch
   every single time, even if you'd just looked at that exact stock a
   few seconds ago.

   This module caches JSON API responses in sessionStorage (survives
   navigation between pages in the same tab, cleared when the tab
   closes) keyed by the exact request URL, with a short TTL matching
   the backend's own cache TTLs. Second visit within the TTL window =
   instant render, zero network call.
   ===================================================== */

const ApiCache = (function () {
    "use strict";

    const PREFIX = "jm_cache::";

    // Matches backend/data/cache.py TTLs: intraday candles move fast
    // and get a short TTL, daily/weekly/monthly can hold longer.
    const TTL_INTRADAY = 20000;  // 20s
    const TTL_DAILY = 90000;     // 90s

    function ttlFor(url) {
        return /interval=(1m|2m|5m|15m|30m|60m|90m)\b/.test(url)
            ? TTL_INTRADAY
            : TTL_DAILY;
    }

    function get(url) {
        try {
            const raw = sessionStorage.getItem(PREFIX + url);
            if (!raw) return null;

            const entry = JSON.parse(raw);
            if (Date.now() > entry.expires) {
                sessionStorage.removeItem(PREFIX + url);
                return null;
            }
            return entry.data;
        } catch (err) {
            // Corrupt entry or storage unavailable (private browsing, etc.)
            return null;
        }
    }

    function set(url, data, ttl) {
        try {
            sessionStorage.setItem(
                PREFIX + url,
                JSON.stringify({ expires: Date.now() + (ttl || ttlFor(url)), data })
            );
        } catch (err) {
            // Storage full or disabled — degrade gracefully, just skip caching.
        }
    }

    /**
     * Fetch JSON for `url`, serving from cache when fresh.
     * Uses window.apiFetch (auth-aware) when available, else plain fetch.
     */
    async function fetchJSON(url, options) {
        const cached = get(url);
        if (cached !== null) {
            return cached;
        }

        const fetcher = typeof apiFetch === "function" ? apiFetch : fetch;
        const response = await fetcher(url, options);

        if (!response.ok) {
            throw new Error(`${url} failed: ${response.status}`);
        }

        const json = await response.json();
        set(url, json);
        return json;
    }

    /** Clear cached entries. Pass a substring to clear only matching URLs. */
    function clear(substring) {
        Object.keys(sessionStorage).forEach((key) => {
            if (key.startsWith(PREFIX) && (!substring || key.includes(substring))) {
                sessionStorage.removeItem(key);
            }
        });
    }

    return { get, set, fetchJSON, clear };
})();

window.ApiCache = ApiCache;
