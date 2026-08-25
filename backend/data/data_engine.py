"""
Central Indian market data engine.

Features:

- Download market data
- Cache locally
- Incrementally update existing cache
- Merge old + new candles
- Remove duplicates
- Validate OHLCV
- Support multiple intervals
- Automatically download missing timeframes
"""

from pathlib import Path

import pandas as pd

from backend.data.market_data import MarketData
from backend.data.indian_stock_universe import get_indian_stocks
from backend.data.symbol_utils import normalize_symbol


class DataEngine:

    CACHE_DIR = (
        Path(__file__).resolve().parent
        / "cache"
        / "market"
    )

    REQUIRED_COLUMNS = [
        "Datetime",
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
    ]

    # ======================================================
    # INIT
    # ======================================================

    def __init__(self):

        self.market = MarketData()

        self.CACHE_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

    # ======================================================
    # SYMBOL
    # ======================================================

    @staticmethod
    def _safe_symbol(symbol):
        """
        Convert symbol into a filesystem-safe name.
        """

        return (
            str(symbol)
            .strip()
            .upper()
            .replace(".", "_")
            .replace("/", "_")
            .replace("\\", "_")
            .replace(" ", "_")
        )

    # ======================================================
    # CACHE PATH
    # ======================================================

    def cache_path(
        self,
        symbol,
        interval="1d",
    ):
        """Return cache path for the canonical symbol + interval."""

        symbol = normalize_symbol(symbol)

        return (
            self.CACHE_DIR
            / (
                f"{self._safe_symbol(symbol)}"
                f"_{interval}.csv"
            )
        )

    # ======================================================
    # NORMALIZE
    # ======================================================

    def _normalize(self, df):
        """
        Normalize downloaded/cached market data.

        Performs:

        - column normalization
        - datetime conversion
        - numeric conversion
        - OHLC validation
        - volume validation
        - duplicate removal
        - chronological sorting
        """

        if df is None or df.empty:
            return None

        df = df.copy()

        # --------------------------------------------------
        # Normalize column names
        # --------------------------------------------------

        df.columns = [
            str(column).strip()
            for column in df.columns
        ]

        # --------------------------------------------------
        # Datetime
        # --------------------------------------------------

        if "Datetime" not in df.columns:

            if "Date" in df.columns:

                df.rename(
                    columns={
                        "Date": "Datetime",
                    },
                    inplace=True,
                )

        if "Datetime" not in df.columns:
            return None

        df["Datetime"] = pd.to_datetime(
            df["Datetime"],
            errors="coerce",
        )

        df.dropna(
            subset=["Datetime"],
            inplace=True,
        )

        # --------------------------------------------------
        # OHLCV
        # --------------------------------------------------

        required_ohlcv = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
        ]

        for column in required_ohlcv:

            if column not in df.columns:
                return None

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

        # --------------------------------------------------
        # Remove invalid rows
        # --------------------------------------------------

        df.dropna(
            subset=required_ohlcv,
            inplace=True,
        )

        if df.empty:
            return None

        # --------------------------------------------------
        # Remove infinity
        # --------------------------------------------------

        df.replace(
            [float("inf"), float("-inf")],
            pd.NA,
            inplace=True,
        )

        df.dropna(
            subset=required_ohlcv,
            inplace=True,
        )

        if df.empty:
            return None

        # --------------------------------------------------
        # OHLC validation
        # --------------------------------------------------

        valid_ohlc = (
            (df["High"] >= df["Low"])
            &
            (df["High"] >= df["Open"])
            &
            (df["High"] >= df["Close"])
            &
            (df["Low"] <= df["Open"])
            &
            (df["Low"] <= df["Close"])
        )

        df = df.loc[valid_ohlc].copy()

        if df.empty:
            return None

        # --------------------------------------------------
        # Volume validation
        # --------------------------------------------------

        df = df.loc[
            df["Volume"] >= 0
        ].copy()

        if df.empty:
            return None

        # --------------------------------------------------
        # Duplicate timestamps
        # --------------------------------------------------

        df.drop_duplicates(
            subset=["Datetime"],
            keep="last",
            inplace=True,
        )

        # --------------------------------------------------
        # Sort
        # --------------------------------------------------

        df.sort_values(
            "Datetime",
            inplace=True,
        )

        # --------------------------------------------------
        # Final columns
        # --------------------------------------------------

        return (
            df[
                self.REQUIRED_COLUMNS
            ]
            .reset_index(drop=True)
        )

    # ======================================================
    # LOAD CACHE
    # ======================================================

    def _load_cached_stock(
        self,
        symbol,
        interval="1d",
    ):
        """
        Load only from local cache.

        Does NOT download.
        """

        path = self.cache_path(
            symbol,
            interval,
        )

        if not path.exists():
            return None

        try:

            df = pd.read_csv(path)

            df = self._normalize(df)

            if df is None or df.empty:

                print(
                    f"[DataEngine] "
                    f"Invalid cache: "
                    f"{symbol} {interval}"
                )

                return None

            return df

        except Exception as exc:

            print(
                f"[DataEngine] "
                f"Cache read failed: "
                f"{symbol} {interval}: {exc}"
            )

            return None

    # ======================================================
    # LOAD STOCK
    # ======================================================

    def load_stock(
        self,
        symbol,
        interval="1d",
        auto_download=False,
        period=None,
    ):
        """
        Load stock data.

        Default behavior:
            cache only

        auto_download=True:
            cache first
            download if cache missing/invalid
        """

        symbol = normalize_symbol(symbol)
        if not symbol:
            return None

        # --------------------------------------------------
        # Try cache
        # --------------------------------------------------

        cached = self._load_cached_stock(
            symbol=symbol,
            interval=interval,
        )

        if cached is not None and not cached.empty:

            return cached

        # --------------------------------------------------
        # Do not download unless explicitly requested
        # --------------------------------------------------

        if not auto_download:

            return None

        # --------------------------------------------------
        # Download
        # --------------------------------------------------

        print(
            f"[DataEngine] "
            f"Cache unavailable. "
            f"Downloading {symbol} "
            f"interval={interval}"
        )

        try:

            return self.download_stock(
                symbol=symbol,
                interval=interval,
                period=period,
            )

        except Exception as exc:

            print(
                f"[DataEngine] "
                f"Download failed: "
                f"{symbol} {interval}: {exc}"
            )

            return None

    # ======================================================
    # LOAD MULTIPLE TIMEFRAMES
    # ======================================================

    def load_timeframes(
        self,
        symbol,
        intervals=None,
        auto_download=True,
    ):
        """
        Load multiple timeframes.

        Example:

            {
                "1d": DataFrame,
                "1h": DataFrame,
                "15m": DataFrame,
            }

        Cache is preferred.

        Missing data is downloaded when
        auto_download=True.
        """

        if intervals is None:

            intervals = [
                "1d",
                "1h",
                "15m",
            ]

        dataframes = {}

        for interval in intervals:

            try:

                df = self.load_stock(
                    symbol=symbol,
                    interval=interval,
                    auto_download=auto_download,
                )

                if (
                    df is None
                    or df.empty
                ):

                    print(
                        f"[DataEngine] "
                        f"No data: "
                        f"{symbol} {interval}"
                    )

                    dataframes[interval] = None

                    continue

                dataframes[interval] = df

                print(
                    f"[DataEngine] "
                    f"{symbol} {interval}: "
                    f"{len(df)} rows"
                )

            except Exception as exc:

                print(
                    f"[DataEngine] "
                    f"Timeframe failed: "
                    f"{symbol} {interval}: "
                    f"{exc}"
                )

                dataframes[interval] = None

        return dataframes

    # ======================================================
    # SAVE CACHE
    # ======================================================

    def save_stock(
        self,
        symbol,
        interval,
        df,
    ):
        """
        Save normalized data to cache.
        """

        if df is None or df.empty:
            return False

        df = self._normalize(df)

        if df is None or df.empty:
            return False

        path = self.cache_path(
            symbol,
            interval,
        )

        try:

            df.to_csv(
                path,
                index=False,
            )

            print(
                f"[DataEngine] Cached: "
                f"{path}"
            )

            return True

        except Exception as exc:

            print(
                f"[DataEngine] "
                f"Cache write failed: "
                f"{symbol} {interval}: {exc}"
            )

            return False

    # ======================================================
    # DOWNLOAD
    # ======================================================

    def download_stock(
        self,
        symbol,
        interval="1d",
        period=None,
    ):
        """
        Full download.

        Existing cache is replaced.
        """

        symbol = normalize_symbol(symbol)
        if not symbol:
            return None

        print(
            f"[DataEngine] "
            f"Downloading {symbol} "
            f"interval={interval}"
        )

        df = self.market.get_data(
            symbol=symbol,
            period=period,
            interval=interval,
        )

        if df is None or df.empty:

            print(
                f"[DataEngine] "
                f"Provider returned no data: "
                f"{symbol} {interval}"
            )

            return None

        df = self._normalize(df)

        if df is None or df.empty:

            print(
                f"[DataEngine] "
                f"Downloaded data invalid: "
                f"{symbol} {interval}"
            )

            return None

        if not self.save_stock(
            symbol=symbol,
            interval=interval,
            df=df,
        ):

            return None

        print(
            f"[DataEngine] "
            f"Downloaded {len(df)} rows: "
            f"{symbol} {interval}"
        )

        return df

    # ======================================================
    # INCREMENTAL UPDATE
    # ======================================================

    def update_stock(
        self,
        symbol,
        interval="1d",
        period=None,
    ):
        """
        Incrementally update one stock.

        Existing cache:
            old candles

        Provider:
            fresh candles

        Result:
            old + fresh
            duplicates removed
            sorted chronologically
        """

        print()
        print("=" * 60)

        print(
            f"[DataEngine] Updating "
            f"{symbol} "
            f"interval={interval}"
        )

        print("=" * 60)

        # --------------------------------------------------
        # Existing cache
        # --------------------------------------------------

        cached = self._load_cached_stock(
            symbol=symbol,
            interval=interval,
        )

        if cached is not None and not cached.empty:

            print(
                f"[DataEngine] "
                f"Existing cache: "
                f"{len(cached)} rows"
            )

            print(
                f"[DataEngine] "
                f"Last cached candle: "
                f"{cached['Datetime'].iloc[-1]}"
            )

        else:

            print(
                "[DataEngine] "
                "No existing cache"
            )

        # --------------------------------------------------
        # Fresh provider data
        # --------------------------------------------------

        try:

            fresh = self.market.get_data(
                symbol=symbol,
                period=period,
                interval=interval,
            )

        except Exception as exc:

            print(
                f"[DataEngine] "
                f"Provider error: "
                f"{symbol} {interval}: {exc}"
            )

            return cached

        if fresh is None or fresh.empty:

            print(
                f"[DataEngine] "
                f"No fresh data: "
                f"{symbol} {interval}"
            )

            return cached

        fresh = self._normalize(
            fresh
        )

        if fresh is None or fresh.empty:

            print(
                f"[DataEngine] "
                f"Fresh data invalid: "
                f"{symbol} {interval}"
            )

            return cached

        print(
            f"[DataEngine] "
            f"Fresh rows: "
            f"{len(fresh)}"
        )

        # --------------------------------------------------
        # No cache
        # --------------------------------------------------

        if cached is None or cached.empty:

            self.save_stock(
                symbol=symbol,
                interval=interval,
                df=fresh,
            )

            return fresh

        # --------------------------------------------------
        # Merge
        # --------------------------------------------------

        combined = pd.concat(
            [
                cached,
                fresh,
            ],
            ignore_index=True,
        )

        combined = self._normalize(
            combined
        )

        if combined is None or combined.empty:

            print(
                f"[DataEngine] "
                f"Merge failed: "
                f"{symbol} {interval}"
            )

            return cached

        # --------------------------------------------------
        # Save
        # --------------------------------------------------

        self.save_stock(
            symbol=symbol,
            interval=interval,
            df=combined,
        )

        added_rows = (
            len(combined)
            - len(cached)
        )

        print(
            f"[DataEngine] "
            f"Final rows: "
            f"{len(combined)}"
        )

        print(
            f"[DataEngine] "
            f"New rows: "
            f"{max(added_rows, 0)}"
        )

        print(
            f"[DataEngine] "
            f"Latest candle: "
            f"{combined['Datetime'].iloc[-1]}"
        )

        return combined

    # ======================================================
    # UPDATE MULTIPLE TIMEFRAMES
    # ======================================================

    def update_timeframes(
        self,
        symbol,
        intervals=None,
    ):
        """
        Incrementally update multiple timeframes.
        """

        if intervals is None:

            intervals = [
                "1d",
                "1h",
                "15m",
            ]

        dataframes = {}

        for interval in intervals:

            try:

                df = self.update_stock(
                    symbol=symbol,
                    interval=interval,
                )

                dataframes[interval] = df

            except Exception as exc:

                print(
                    f"[DataEngine] "
                    f"Update failed: "
                    f"{symbol} {interval}: {exc}"
                )

                dataframes[interval] = None

        return dataframes

    # ======================================================
    # UNIVERSE
    # ======================================================

    def build_universe(
        self,
        symbols=None,
        interval="1d",
        period=None,
        incremental=False,
    ):
        """
        Download/update an entire stock universe.
        """

        symbols = (
            symbols
            if symbols is not None
            else get_indian_stocks()
        )

        successful = []
        failed = []
        total_rows = 0

        for symbol in symbols:

            try:

                if incremental:

                    df = self.update_stock(
                        symbol=symbol,
                        interval=interval,
                        period=period,
                    )

                else:

                    df = self.download_stock(
                        symbol=symbol,
                        interval=interval,
                        period=period,
                    )

            except Exception as exc:

                print(
                    f"[DataEngine] "
                    f"Universe error "
                    f"{symbol}: {exc}"
                )

                df = None

            if df is None or df.empty:

                failed.append(symbol)

                continue

            successful.append(symbol)

            total_rows += len(df)

        return {
            "success": bool(successful),

            "total": len(symbols),

            "successful": len(
                successful
            ),

            "failed": len(
                failed
            ),

            "successful_symbols": (
                successful
            ),

            "failed_symbols": (
                failed
            ),

            "rows": total_rows,
        }

        # ======================================================
    # LOAD MULTIPLE TIMEFRAMES
    # ======================================================

    def load_multiple_timeframes(
        self,
        symbol,
        intervals=None,
        auto_download=True,
    ):
        """
        Load multiple timeframes.

        Returns:
            {
                "1d": DataFrame or None,
                "1h": DataFrame or None,
                "15m": DataFrame or None,
            }
        """

        if intervals is None:
            intervals = [
                "1d",
                "1h",
                "15m",
            ]

        dataframes = {}

        for interval in intervals:

            try:

                df = self.load_stock(
                    symbol=symbol,
                    interval=interval,
                    auto_download=auto_download,
                )

                if df is None or df.empty:

                    print(
                        f"[DataEngine] "
                        f"No data: "
                        f"{symbol} {interval}"
                    )

                    dataframes[interval] = None
                    continue

                dataframes[interval] = df

                print(
                    f"[DataEngine] "
                    f"{symbol} {interval}: "
                    f"{len(df)} rows"
                )

            except Exception as exc:

                print(
                    f"[DataEngine] "
                    f"Timeframe failed: "
                    f"{symbol} {interval}: "
                    f"{exc}"
                )

                dataframes[interval] = None

        return dataframes