import numpy as np
import ta


class Indicators:

    @staticmethod
    def calculate(df):

        df = df.copy()

        # =========================================================
        # EXISTING TECHNICAL INDICATORS
        # =========================================================

        df["RSI"] = ta.momentum.RSIIndicator(
            df["Close"]
        ).rsi()

        macd = ta.trend.MACD(
            df["Close"]
        )

        df["MACD"] = macd.macd()
        df["MACD_SIGNAL"] = macd.macd_signal()

        df["EMA20"] = ta.trend.EMAIndicator(
            df["Close"],
            window=20
        ).ema_indicator()

        df["EMA50"] = ta.trend.EMAIndicator(
            df["Close"],
            window=50
        ).ema_indicator()

        df["EMA200"] = ta.trend.EMAIndicator(
            df["Close"],
            window=200
        ).ema_indicator()

        df["ATR"] = ta.volatility.AverageTrueRange(
            df["High"],
            df["Low"],
            df["Close"]
        ).average_true_range()

        bb = ta.volatility.BollingerBands(
            df["Close"]
        )

        df["BB_UPPER"] = bb.bollinger_hband()
        df["BB_LOWER"] = bb.bollinger_lband()

        df["ADX"] = ta.trend.ADXIndicator(
            df["High"],
            df["Low"],
            df["Close"]
        ).adx()

        df["OBV"] = ta.volume.OnBalanceVolumeIndicator(
            df["Close"],
            df["Volume"]
        ).on_balance_volume()

        # =========================================================
        # CANDLESTICK / PRICE ACTION FEATURES
        # =========================================================

        open_price = df["Open"]
        high = df["High"]
        low = df["Low"]
        close = df["Close"]

        # ---------------------------------------------------------
        # Candle body
        # ---------------------------------------------------------

        df["CANDLE_BODY"] = (
            close - open_price
        ).abs()

        # ---------------------------------------------------------
        # Candle range
        # ---------------------------------------------------------

        df["CANDLE_RANGE"] = (
            high - low
        )

        # ---------------------------------------------------------
        # Upper wick
        # ---------------------------------------------------------

        df["UPPER_WICK"] = (
            high
            - np.maximum(
                open_price,
                close
            )
        )

        # ---------------------------------------------------------
        # Lower wick
        # ---------------------------------------------------------

        df["LOWER_WICK"] = (
            np.minimum(
                open_price,
                close
            )
            - low
        )

        # ---------------------------------------------------------
        # Avoid division by zero
        # ---------------------------------------------------------

        safe_range = (
            df["CANDLE_RANGE"]
            .replace(0, np.nan)
        )

        # ---------------------------------------------------------
        # Body ratio
        # ---------------------------------------------------------

        df["BODY_RATIO"] = (
            df["CANDLE_BODY"]
            / safe_range
        )

        # ---------------------------------------------------------
        # Wick ratios
        # ---------------------------------------------------------

        df["UPPER_WICK_RATIO"] = (
            df["UPPER_WICK"]
            / safe_range
        )

        df["LOWER_WICK_RATIO"] = (
            df["LOWER_WICK"]
            / safe_range
        )

        # ---------------------------------------------------------
        # Candle direction
        #
        #  1 = bullish
        # -1 = bearish
        #  0 = neutral
        # ---------------------------------------------------------

        df["CANDLE_DIRECTION"] = np.where(
            close > open_price,
            1,
            np.where(
                close < open_price,
                -1,
                0
            )
        )

        # =========================================================
        # COMMON CANDLE CONDITIONS
        # =========================================================

        bullish = (
            close > open_price
        )

        bearish = (
            close < open_price
        )

        body = df["CANDLE_BODY"]

        # =========================================================
        # DOJI
        # =========================================================

        df["DOJI"] = (
            df["BODY_RATIO"] <= 0.10
        ).astype(int)

        # =========================================================
        # PREVIOUS CANDLE DATA
        #
        # IMPORTANT:
        # Only previous candles are used.
        # No future candle information is used.
        # =========================================================

        previous_open = (
            open_price.shift(1)
        )

        previous_close = (
            close.shift(1)
        )

        previous_body = (
            previous_close
            - previous_open
        )

        previous_body_abs = (
            previous_body.abs()
        )

        previous_range = (
            df["CANDLE_RANGE"].shift(1)
        )

        # =========================================================
        # TREND CONTEXT
        #
        # We intentionally use previous candles only.
        # =========================================================

        previous_close_2 = (
            close.shift(2)
        )

        previous_close_3 = (
            close.shift(3)
        )

        # Two-candle downtrend
        downtrend_2 = (
            previous_close
            < previous_close_2
        )

        # Three-candle downtrend
        downtrend_3 = (
            (previous_close < previous_close_2)
            &
            (previous_close_2 < previous_close_3)
        )

        # Two-candle uptrend
        uptrend_2 = (
            previous_close
            > previous_close_2
        )

        # Three-candle uptrend
        uptrend_3 = (
            (previous_close > previous_close_2)
            &
            (previous_close_2 > previous_close_3)
        )

        prior_downtrend = (
            downtrend_2
            | downtrend_3
        )

        prior_uptrend = (
            uptrend_2
            | uptrend_3
        )

        # =========================================================
        # HAMMER / HANGING MAN SHAPE
        # =========================================================

        hammer_shape = (
            (df["LOWER_WICK_RATIO"] >= 0.50)
            &
            (df["UPPER_WICK_RATIO"] <= 0.20)
            &
            (df["BODY_RATIO"] <= 0.40)
        )

        # =========================================================
        # HAMMER
        #
        # Hammer = hammer-shaped candle after a downtrend.
        # =========================================================

        df["HAMMER"] = (
            hammer_shape
            &
            prior_downtrend
        ).astype(int)

        # =========================================================
        # HANGING MAN
        #
        # Hanging Man = same physical shape,
        # but after an uptrend.
        # =========================================================

        df["HANGING_MAN"] = (
            hammer_shape
            &
            prior_uptrend
        ).astype(int)

        # =========================================================
        # INVERTED HAMMER / SHOOTING STAR SHAPE
        # =========================================================

        inverted_shape = (
            (df["UPPER_WICK_RATIO"] >= 0.50)
            &
            (df["LOWER_WICK_RATIO"] <= 0.20)
            &
            (df["BODY_RATIO"] <= 0.40)
        )

        # =========================================================
        # INVERTED HAMMER
        #
        # Inverted hammer after a downtrend.
        # =========================================================

        df["INVERTED_HAMMER"] = (
            inverted_shape
            &
            prior_downtrend
        ).astype(int)

        # =========================================================
        # SHOOTING STAR
        #
        # Shooting star after an uptrend.
        # =========================================================

        df["SHOOTING_STAR"] = (
            inverted_shape
            &
            prior_uptrend
        ).astype(int)

        # =========================================================
        # BULLISH ENGULFING
        # =========================================================

        previous_bearish = (
            previous_close
            < previous_open
        )

        current_bullish = (
            close
            > open_price
        )

        df["BULLISH_ENGULFING"] = (
            previous_bearish
            &
            current_bullish
            &
            (open_price <= previous_close)
            &
            (close >= previous_open)
            &
            (body > previous_body_abs)
        ).astype(int)

        # =========================================================
        # BEARISH ENGULFING
        # =========================================================

        previous_bullish = (
            previous_close
            > previous_open
        )

        current_bearish = (
            close
            < open_price
        )

        df["BEARISH_ENGULFING"] = (
            previous_bullish
            &
            current_bearish
            &
            (open_price >= previous_close)
            &
            (close <= previous_open)
            &
            (body > previous_body_abs)
        ).astype(int)

        # =========================================================
        # THREE-CANDLE DATA
        # =========================================================

        # Candle 1 = two candles ago
        candle1_open = (
            open_price.shift(2)
        )

        candle1_close = (
            close.shift(2)
        )

        candle1_body = (
            df["CANDLE_BODY"].shift(2)
        )

        candle1_range = (
            df["CANDLE_RANGE"].shift(2)
        )

        # Candle 2 = previous candle
        candle2_body = (
            df["CANDLE_BODY"].shift(1)
        )

        candle2_range = (
            df["CANDLE_RANGE"].shift(1)
        )

        # Candle 1 midpoint
        candle1_midpoint = (
            candle1_open
            + (
                candle1_close
                - candle1_open
            ) * 0.50
        )

        # =========================================================
        # CANDLE 1 STRENGTH
        # =========================================================

        candle1_strong = (
            candle1_body
            >=
            candle1_range * 0.50
        )

        # =========================================================
        # CANDLE 2 SMALL BODY
        #
        # This is the important correction.
        #
        # The old implementation effectively compared
        # the previous candle against itself.
        # =========================================================

        candle2_small = (
            candle2_body
            <=
            candle2_range * 0.30
        )

        # =========================================================
        # MORNING STAR
        #
        # Candle 1:
        #   Strong bearish
        #
        # Candle 2:
        #   Small body
        #
        # Candle 3:
        #   Bullish
        #
        # Candle 3 closes above Candle 1 midpoint.
        #
        # Requires previous downtrend.
        # =========================================================

        candle1_bearish = (
            candle1_close
            < candle1_open
        )

        candle3_bullish = (
            close
            > open_price
        )

        df["MORNING_STAR"] = (
            prior_downtrend
            &
            candle1_bearish
            &
            candle1_strong
            &
            candle2_small
            &
            candle3_bullish
            &
            (close > candle1_midpoint)
        ).astype(int)

        # =========================================================
        # EVENING STAR
        #
        # Candle 1:
        #   Strong bullish
        #
        # Candle 2:
        #   Small body
        #
        # Candle 3:
        #   Bearish
        #
        # Candle 3 closes below Candle 1 midpoint.
        #
        # Requires previous uptrend.
        # =========================================================

        candle1_bullish = (
            candle1_close
            > candle1_open
        )

        candle3_bearish = (
            close
            < open_price
        )

        df["EVENING_STAR"] = (
            prior_uptrend
            &
            candle1_bullish
            &
            candle1_strong
            &
            candle2_small
            &
            candle3_bearish
            &
            (close < candle1_midpoint)
        ).astype(int)

        # =========================================================
        # FINAL CLEANUP
        # =========================================================

        # Pattern columns must always be integer flags.
        pattern_columns = [
            "DOJI",
            "HAMMER",
            "INVERTED_HAMMER",
            "SHOOTING_STAR",
            "HANGING_MAN",
            "BULLISH_ENGULFING",
            "BEARISH_ENGULFING",
            "MORNING_STAR",
            "EVENING_STAR",
        ]

        for column in pattern_columns:
            df[column] = (
                df[column]
                .fillna(0)
                .astype(int)
            )

        return df