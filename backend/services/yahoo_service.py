import yfinance as yf
import pandas as pd

from backend.data.symbol_utils import normalize_symbol
from backend.data.cache import cache_get, cache_set, TTL_INTRADAY, TTL_DAILY


class YahooService:

    PERIOD_MAPPING = {
        "1m": ("7d", "1m"),
        "2m": ("60d", "2m"),
        "5m": ("60d", "5m"),
        "15m": ("60d", "15m"),
        "30m": ("60d", "30m"),
        "60m": ("730d", "60m"),
        "90m": ("60d", "90m"),
        "1h": ("730d", "60m"),
        "1d": ("5y", "1d"),
        "5d": ("10y", "5d"),
        "1wk": ("10y", "1wk"),
        "1mo": ("max", "1mo"),
    }

    # ==========================================================
    # DOWNLOAD HISTORY
    # ==========================================================

    @staticmethod
    def _download_history(symbol, period, interval):
        """
        Download historical OHLCV data from Yahoo Finance.

        Returns:
            pandas.DataFrame or None
        """

        try:

            print(
                f"[Yahoo] Downloading {symbol} "
                f"period={period} interval={interval}"
            )

            df = yf.download(
                symbol,
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=False,
                prepost=False,
                threads=False,
            )

        except Exception as e:

            print(
                f"[Yahoo] Download error for "
                f"{symbol} "
                f"({period}, {interval}): {e}"
            )

            return None

        # ------------------------------------------------------
        # Empty response
        # ------------------------------------------------------

        if df is None or df.empty:

            print(
                f"[Yahoo] Empty response for "
                f"{symbol} "
                f"({period}, {interval})"
            )

            return None

        # ------------------------------------------------------
        # Normalize MultiIndex
        # ------------------------------------------------------

        if isinstance(df.columns, pd.MultiIndex):

            required = {
                "Open",
                "High",
                "Low",
                "Close",
                "Volume",
            }

            level_0 = {
                str(x)
                for x in df.columns.get_level_values(0)
            }

            level_1 = {
                str(x)
                for x in df.columns.get_level_values(1)
            }

            # Example:
            #
            # Price       Close      High ...
            # Ticker      INFY.NS    INFY.NS
            #

            if required.issubset(level_0):

                df.columns = (
                    df.columns
                    .get_level_values(0)
                )

            elif required.issubset(level_1):

                df.columns = (
                    df.columns
                    .get_level_values(1)
                )

            else:

                # Last-resort flattening

                df.columns = [
                    column[0]
                    if isinstance(column, tuple)
                    else column
                    for column in df.columns
                ]

        # ------------------------------------------------------
        # Normalize column names
        # ------------------------------------------------------

        df.columns = [
            str(column)
            for column in df.columns
        ]

        # ------------------------------------------------------
        # Validate required columns
        # ------------------------------------------------------

        required = {
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
        }

        missing = required.difference(
            set(df.columns)
        )

        if missing:

            print(
                f"[Yahoo] Missing columns for "
                f"{symbol}: {sorted(missing)}"
            )

            print(
                f"[Yahoo] Available columns: "
                f"{list(df.columns)}"
            )

            return None

        # ------------------------------------------------------
        # Convert OHLCV to numeric
        # ------------------------------------------------------

        for column in [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
        ]:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

        # ------------------------------------------------------
        # Remove invalid OHLC rows
        # ------------------------------------------------------

        df = df.dropna(
            subset=[
                "Open",
                "High",
                "Low",
                "Close",
            ]
        )

        if df.empty:

            print(
                f"[Yahoo] No valid OHLC rows "
                f"for {symbol}"
            )

            return None

        # ------------------------------------------------------
        # Sort chronologically
        # ------------------------------------------------------

        df = df.sort_index()

        # ------------------------------------------------------
        # Remove duplicate timestamps
        # ------------------------------------------------------

        df = df[
            ~df.index.duplicated(
                keep="last"
            )
        ]

        print(
            f"[Yahoo] Downloaded "
            f"{len(df)} candles for {symbol}"
        )

        # ------------------------------------------------------
        # IMPORTANT
        # ------------------------------------------------------

        return df

    # ==========================================================
    # GET STOCK
    # ==========================================================

    @classmethod
    def get_stock(
        cls,
        symbol="RELIANCE.NS",
        interval="1d",
        period=None,
    ):

        # ------------------------------------------------------
        # Validate symbol
        # ------------------------------------------------------

        if not symbol:

            print(
                "[Yahoo] Empty symbol"
            )

            return None

        symbol = normalize_symbol(symbol)

        if not symbol:
            print("[Yahoo] Invalid symbol")
            return None

        # ------------------------------------------------------
        # Resolve period / interval
        # ------------------------------------------------------

        if period is None:

            period, interval = (
                cls.PERIOD_MAPPING.get(
                    interval,
                    ("5y", "1d"),
                )
            )

        # ------------------------------------------------------
        # CACHE — load once, don't hit network/disk again until TTL
        # expires. This is the #1 fix for slow page loads: without
        # this, every dashboard refresh / chart open / scan re-downloads
        # the same candles from Yahoo Finance from scratch.
        # ------------------------------------------------------

        cache_key = ("yahoo_stock", symbol, interval, period)
        cached_result = cache_get(cache_key)

        if cached_result is not None:
            # Return a shallow copy so callers that mutate the DataFrame
            # (adding indicator columns, etc.) never corrupt the cached
            # entry for the next caller.
            result = dict(cached_result)
            result["df"] = cached_result["df"].copy()
            return result

        print(
            f"[Yahoo] Loading {symbol} "
            f"period={period} "
            f"interval={interval}"
        )

        # ======================================================
        # PRIMARY HISTORY REQUEST
        # ======================================================

        history_df = cls._download_history(
            symbol=symbol,
            period=period,
            interval=interval,
        )

        # ------------------------------------------------------
        # Primary request status
        # ------------------------------------------------------

        if (
            history_df is not None
            and not history_df.empty
        ):

            print(
                f"[Yahoo] Primary request successful: "
                f"{len(history_df)} candles"
            )

        else:

            print(
                f"[Yahoo] Primary request failed "
                f"for {symbol}"
            )

        # ======================================================
        # FALLBACK HISTORY
        # ======================================================

        if (
            history_df is None
            or history_df.empty
        ):

            # --------------------------------------------------
            # Daily / weekly / monthly
            # --------------------------------------------------

            if interval in (
                "1d",
                "5d",
                "1wk",
                "1mo",
            ):

                fallback_periods = [
                    "2y",
                    "1y",
                ]

            # --------------------------------------------------
            # Intraday
            # --------------------------------------------------

            else:

                fallback_periods = [
                    "6mo",
                    "60d",
                    "30d",
                    "7d",
                ]

            for fallback_period in fallback_periods:

                print(
                    f"[Yahoo] Trying fallback "
                    f"{symbol}: "
                    f"period={fallback_period} "
                    f"interval={interval}"
                )

                history_df = (
                    cls._download_history(
                        symbol=symbol,
                        period=fallback_period,
                        interval=interval,
                    )
                )

                if (
                    history_df is not None
                    and not history_df.empty
                ):

                    print(
                        f"[Yahoo] Fallback successful "
                        f"for {symbol}: "
                        f"{len(history_df)} candles"
                    )

                    break

        # ======================================================
        # NO HISTORY
        # ======================================================

        if (
            history_df is None
            or history_df.empty
        ):

            print(
                f"[Yahoo] No historical data "
                f"available for {symbol}"
            )

            return None

        # ======================================================
        # CLEAN DATA
        # ======================================================

        history_df = history_df.copy()

        history_df = history_df.dropna(
            subset=[
                "Open",
                "High",
                "Low",
                "Close",
            ]
        )

        if history_df.empty:

            print(
                f"[Yahoo] Historical data became "
                f"empty after cleaning for {symbol}"
            )

            return None

        # ======================================================
        # NUMERIC CONVERSION
        # ======================================================

        for column in [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
        ]:

            if column in history_df.columns:

                history_df[column] = pd.to_numeric(
                    history_df[column],
                    errors="coerce",
                )

        history_df = history_df.dropna(
            subset=["Close"]
        )

        if history_df.empty:

            return None

        # ======================================================
        # YAHOO INFO
        # ======================================================

        info = {}

        try:

            ticker = yf.Ticker(
                symbol
            )

            info = ticker.info or {}

        except Exception as e:

            print(
                f"[Yahoo] Info unavailable "
                f"for {symbol}: {e}"
            )

            info = {}

        # ======================================================
        # TECHNICAL INDICATORS
        # ======================================================

        # ------------------------------------------------------
        # EMA20
        # ------------------------------------------------------

        history_df["EMA20"] = (
            history_df["Close"]
            .ewm(
                span=20,
                adjust=False,
            )
            .mean()
        )

        # ------------------------------------------------------
        # EMA50
        # ------------------------------------------------------

        history_df["EMA50"] = (
            history_df["Close"]
            .ewm(
                span=50,
                adjust=False,
            )
            .mean()
        )

        # ------------------------------------------------------
        # SMA200
        # ------------------------------------------------------

        history_df["SMA200"] = (
            history_df["Close"]
            .rolling(
                window=200
            )
            .mean()
        )

        # ------------------------------------------------------
        # RSI
        # ------------------------------------------------------

        delta = (
            history_df["Close"]
            .diff()
        )

        gain = (
            delta
            .where(
                delta > 0,
                0
            )
            .rolling(
                window=14
            )
            .mean()
        )

        loss = (
            -delta
            .where(
                delta < 0,
                0
            )
            .rolling(
                window=14
            )
            .mean()
        )

        rs = gain / loss

        history_df["RSI"] = (
            100
            - (
                100
                / (
                    1 + rs
                )
            )
        )

        # ======================================================
        # CHART DATA
        # ======================================================

        candles = []

        volume = []

        ema20 = []

        ema50 = []

        sma200 = []

        rsi = []

        # ------------------------------------------------------
        # Generate chart arrays (vectorized)
        #
        # The old version looped row-by-row with .iterrows(), which is
        # one of the slowest patterns in pandas — for 5 years of daily
        # candles that's ~1250 Python-level iterations, each building a
        # dict field-by-field, on EVERY uncached request. Building the
        # same arrays with numpy/vector ops is 20-50x faster and keeps
        # chart open / dashboard refresh feeling instant even on a cold
        # cache.
        # ------------------------------------------------------

        ts_series = (history_df.index.asi8 // 10**9).astype(int)

        opens = history_df["Open"].to_numpy()
        highs = history_df["High"].to_numpy()
        lows = history_df["Low"].to_numpy()
        closes = history_df["Close"].to_numpy()
        volumes = history_df["Volume"].fillna(0).to_numpy()

        up_color = "#22c55e"
        down_color = "#ef4444"

        candles = [
            {
                "time": int(t),
                "open": round(float(o), 2),
                "high": round(float(h), 2),
                "low": round(float(l), 2),
                "close": round(float(c), 2),
            }
            for t, o, h, l, c in zip(ts_series, opens, highs, lows, closes)
        ]

        volume = [
            {
                "time": int(t),
                "value": int(v),
                "color": up_color if c >= o else down_color,
            }
            for t, v, c, o in zip(ts_series, volumes, closes, opens)
        ]

        def _series_to_points(column_name):
            """Build [{time, value}] points, skipping NaN (e.g. warm-up
            period before an indicator like SMA200 has enough candles)."""
            values = history_df[column_name]
            mask = values.notna().to_numpy()
            valid_ts = ts_series[mask]
            valid_vals = values.to_numpy()[mask]
            return [
                {"time": int(t), "value": round(float(v), 2)}
                for t, v in zip(valid_ts, valid_vals)
            ]

        ema20 = _series_to_points("EMA20")
        ema50 = _series_to_points("EMA50")
        sma200 = _series_to_points("SMA200")
        rsi = _series_to_points("RSI")

        # ======================================================
        # CURRENT PRICE
        # ======================================================

        latest_close = float(
            history_df[
                "Close"
            ].iloc[-1]
        )

        previous_close = (

            float(
                history_df[
                    "Close"
                ].iloc[-2]
            )

            if len(
                history_df
            ) > 1

            else latest_close
        )

        # ======================================================
        # COMPANY NAME
        # ======================================================

        company = info.get(
            "longName"
        )

        if not company:

            if symbol == "INFY.NS":

                company = (
                    "Infosys Limited"
                )

            else:

                company = symbol

        # ======================================================
        # CURRENT PRICE
        # ======================================================

        current_price = info.get(
            "currentPrice"
        )

        if current_price is None:

            current_price = (
                latest_close
            )

        # ======================================================
        # RETURN
        # ======================================================

        result = {

            "symbol": symbol,

            "company": company,

            "sector": info.get(
                "sector",
                "",
            ),

            "industry": info.get(
                "industry",
                "",
            ),

            "marketCap": info.get(
                "marketCap",
                0,
            ),

            "price": float(
                current_price
            ),

            "previousClose": float(
                info.get(
                    "previousClose",
                    previous_close,
                )
            ),

            "dayHigh": float(
                info.get(
                    "dayHigh",
                    history_df[
                        "High"
                    ].iloc[-1],
                )
            ),

            "dayLow": float(
                info.get(
                    "dayLow",
                    history_df[
                        "Low"
                    ].iloc[-1],
                )
            ),

            # --------------------------------------------------
            # Frontend chart data
            # --------------------------------------------------

            "history": candles,

            "volume": volume,

            "ema20": ema20,

            "ema50": ema50,

            "sma200": sma200,

            "rsi": rsi,

            # --------------------------------------------------
            # Raw DataFrame for AI / ML / strategies
            # --------------------------------------------------

            "df": history_df,
        }

        # ------------------------------------------------------
        # Store in cache for next call. Intraday intervals get a
        # short TTL (prices move fast); daily/weekly/monthly get a
        # longer TTL since a candle only closes once a day anyway.
        # ------------------------------------------------------

        ttl = TTL_DAILY if interval in ("1d", "5d", "1wk", "1mo") else TTL_INTRADAY

        cache_set(cache_key, result, ttl=ttl)

        # Return a copy of the df so the cached entry stays pristine
        # even if this first caller mutates it.
        out = dict(result)
        out["df"] = history_df.copy()
        return out