import pandas as pd
import yfinance as yf

from backend.data.data_provider import DataProvider
from backend.data.symbol_utils import normalize_symbol


class YahooProvider(DataProvider):

    def get_data(
        self,
        symbol,
        period="2y",
        interval="1d",
    ):
        if not symbol:
            return None

        symbol = normalize_symbol(symbol)
        if not symbol:
            return None

        try:
            ticker = yf.Ticker(symbol)

            df = ticker.history(
                period=period,
                interval=interval,
                auto_adjust=True,
                actions=False,
            )

            if df is None or df.empty:
                return None

            df = df.copy()

            if isinstance(
                df.index,
                pd.DatetimeIndex,
            ):
                try:
                    if df.index.tz is not None:
                        df.index = (
                            df.index.tz_localize(None)
                        )
                except Exception:
                    pass

            df.reset_index(inplace=True)

            df.columns = [
                str(column).strip()
                for column in df.columns
            ]

            required = [
                "Open",
                "High",
                "Low",
                "Close",
                "Volume",
            ]

            missing = [
                column
                for column in required
                if column not in df.columns
            ]

            if missing:
                return None

            for column in required:
                df[column] = pd.to_numeric(
                    df[column],
                    errors="coerce",
                )

            df = df.dropna(
                subset=required
            )

            df = df[
                df["Volume"] >= 0
            ]

            if df.empty:
                return None

            return (
                df
                .reset_index(drop=True)
            )

        except Exception as exc:
            print(
                f"[YahooProvider] "
                f"{symbol}: {exc}"
            )
            return None
