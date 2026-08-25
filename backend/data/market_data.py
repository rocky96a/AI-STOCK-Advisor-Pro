"""
Central market-data engine.

Responsibilities:
    - normalize Indian symbols
    - retrieve OHLCV data
    - support multiple timeframes
    - retry temporary provider failures
    - normalize Yahoo dataframe structure
    - return clean data
"""

import time

import pandas as pd
import yfinance as yf

from backend.data.symbol_utils import normalize_symbol


class MarketData:

    INTERVAL_CONFIG = {
        "1m": {
            "period": "7d",
        },
        "5m": {
            "period": "60d",
        },
        "15m": {
            "period": "60d",
        },
        "30m": {
            "period": "60d",
        },
        "60m": {
            "period": "730d",
        },
        "1h": {
            "period": "730d",
        },
        "1d": {
            "period": "2y",
        },
        "1wk": {
            "period": "10y",
        },
        "1mo": {
            "period": "max",
        },
    }

    REQUIRED_COLUMNS = [
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
    ]

    def get_data(
        self,
        symbol,
        period=None,
        interval="1d",
        retries=3,
    ):
        """
        Get clean OHLCV data for an Indian stock.

        Returns:
            pandas.DataFrame | None
        """

        symbol = normalize_symbol(symbol)

        if not symbol:
            return None

        if interval not in self.INTERVAL_CONFIG:
            raise ValueError(
                f"Unsupported interval: {interval}"
            )

        if period is None:
            period = self.INTERVAL_CONFIG[
                interval
            ]["period"]

        for attempt in range(
            1,
            retries + 1,
        ):

            try:

                print(
                    f"[MarketData] "
                    f"Yahoo: {symbol} "
                    f"interval={interval} "
                    f"period={period} "
                    f"attempt={attempt}"
                )

                ticker = yf.Ticker(symbol)

                df = ticker.history(
                    period=period,
                    interval=interval,
                    auto_adjust=True,
                    actions=False,
                )

                if df is None or df.empty:
                    raise ValueError(
                        "Provider returned no data"
                    )

                df = self._normalize(df)

                if df is not None and not df.empty:

                    print(
                        f"[MarketData] "
                        f"{symbol}: "
                        f"{len(df)} rows"
                    )

                    return df

            except Exception as exc:

                print(
                    f"[MarketData] "
                    f"{symbol} failed: {exc}"
                )

                if attempt < retries:
                    time.sleep(
                        min(
                            attempt * 2,
                            5,
                        )
                    )

        print(
            f"[MarketData] "
            f"No usable data for {symbol}"
        )

        return None

    def _normalize(self, df):
        """Normalize provider output."""

        df = df.copy()

        # Flatten MultiIndex columns.
        if isinstance(
            df.columns,
            pd.MultiIndex,
        ):
            df.columns = [
                column[0]
                if isinstance(column, tuple)
                else column
                for column in df.columns
            ]

        # Remove timezone.
        if isinstance(
            df.index,
            pd.DatetimeIndex,
        ):
            try:
                if df.index.tz is not None:
                    df.index = (
                        df.index
                        .tz_localize(None)
                    )
            except Exception:
                pass

        df.reset_index(
            inplace=True
        )

        df.columns = [
            str(column).strip()
            for column in df.columns
        ]

        # Yahoo may call the timestamp
        # Date or Datetime.
        if "Datetime" not in df.columns:
            if "Date" in df.columns:
                df.rename(
                    columns={
                        "Date": "Datetime"
                    },
                    inplace=True,
                )

        missing = [
            column
            for column in self.REQUIRED_COLUMNS
            if column not in df.columns
        ]

        if missing:
            print(
                "[MarketData] "
                f"Missing columns: {missing}"
            )
            return None

        for column in self.REQUIRED_COLUMNS:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

        df.dropna(
            subset=self.REQUIRED_COLUMNS,
            inplace=True,
        )

        df = df[
            df["Volume"] >= 0
        ]

        if df.empty:
            return None

        return (
            df
            .sort_values(
                "Datetime"
            )
            .drop_duplicates(
                subset=["Datetime"]
            )
            .reset_index(drop=True)
        )

    def get_latest(
        self,
        symbol,
        interval="1m",
    ):
        """
        Return the latest available candle.
        """

        df = self.get_data(
            symbol,
            interval=interval,
        )

        if df is None or df.empty:
            return None

        return df.iloc[-1].to_dict()