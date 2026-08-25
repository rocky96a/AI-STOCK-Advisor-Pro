import numpy as np
import pandas as pd



class LabelBuilder:
    """
    Outcome-based trading labels.

    LABEL:
        0 = SELL
        1 = HOLD
        2 = BUY

    Decision process:
        Candle i      -> decision
        Candle i + 1  -> entry at Open
        Future candles -> TARGET / STOP / TIME

    IMPORTANT:
        Direction is determined from information available at
        decision candle i.

        Future prices are used only to determine whether that
        already-selected setup was profitable.

    Final invariant:

        LABEL == 0 -> TRADE_DIRECTION == "SELL"
        LABEL == 1 -> TRADE_DIRECTION == "NONE"
        LABEL == 2 -> TRADE_DIRECTION == "BUY"
    """

    # =========================================================
    # TRADE PARAMETERS
    # =========================================================

    ATR_SL_MULTIPLIER = 1.0
    ATR_TARGET_MULTIPLIER = 1.5

    MAX_HOLDING_PERIOD = 10

    # One-way assumptions.
    BROKERAGE_RATE = 0.00025
    SLIPPAGE_RATE = 0.00025

    # Total round-trip cost.
    ROUND_TRIP_COST = (
        2.0 * (BROKERAGE_RATE + SLIPPAGE_RATE)
    )

    # Minimum net return required for BUY/SELL label.
    MIN_EDGE = 0.002

    # =========================================================
    # BUILD LABELS
    # =========================================================

    @staticmethod
    def build(df):

        if df is None:
            raise ValueError(
                "LabelBuilder received None dataframe."
            )

        df = df.copy()

        required_columns = [
            "Open",
            "High",
            "Low",
            "Close",
            "ATR",
        ]

        missing = [
            column
            for column in required_columns
            if column not in df.columns
        ]

        if missing:
            raise ValueError(
                f"LabelBuilder missing columns: {missing}"
            )

        # -----------------------------------------------------
        # Initialize output columns
        # -----------------------------------------------------

        df["ENTRY_PRICE"] = np.nan

        df["BUY_SL"] = np.nan
        df["BUY_TARGET"] = np.nan

        df["SELL_SL"] = np.nan
        df["SELL_TARGET"] = np.nan

        # Default = HOLD.
        df["LABEL"] = 1

        # Actionable direction.
        df["TRADE_DIRECTION"] = "NONE"

        df["SETUP_DIRECTION"] = "NONE"

        # Result of attempted setup.
        df["TRADE_RETURN"] = 0.0

        df["HOLDING_PERIOD"] = 0

        df["EXIT_REASON"] = "NO_TRADE"

        # -----------------------------------------------------
        # Process every decision candle.
        #
        # Last candle cannot be used because there is no
        # next candle available for entry.
        # -----------------------------------------------------

        for i in range(len(df) - 1):

            atr = df["ATR"].iloc[i]

            if pd.isna(atr) or not np.isfinite(atr) or atr <= 0:
                continue

            entry_index = i + 1

            entry = float(
                df["Open"].iloc[entry_index]
            )

            if not np.isfinite(entry) or entry <= 0:
                continue

            # -------------------------------------------------
            # Entry / risk levels
            # -------------------------------------------------

            buy_sl = (
                entry
                - LabelBuilder.ATR_SL_MULTIPLIER * atr
            )

            buy_target = (
                entry
                + LabelBuilder.ATR_TARGET_MULTIPLIER * atr
            )

            sell_sl = (
                entry
                + LabelBuilder.ATR_SL_MULTIPLIER * atr
            )

            sell_target = (
                entry
                - LabelBuilder.ATR_TARGET_MULTIPLIER * atr
            )

            df.iloc[
                i,
                df.columns.get_loc("ENTRY_PRICE")
            ] = entry

            df.iloc[
                i,
                df.columns.get_loc("BUY_SL")
            ] = buy_sl

            df.iloc[
                i,
                df.columns.get_loc("BUY_TARGET")
            ] = buy_target

            df.iloc[
                i,
                df.columns.get_loc("SELL_SL")
            ] = sell_sl

            df.iloc[
                i,
                df.columns.get_loc("SELL_TARGET")
            ] = sell_target

            # -------------------------------------------------
            # DECISION-TIME INFORMATION ONLY
            # -------------------------------------------------

            close = float(
                df["Close"].iloc[i]
            )

            ema20 = (
                df["EMA20"].iloc[i]
                if "EMA20" in df.columns
                else np.nan
            )

            ema50 = (
                df["EMA50"].iloc[i]
                if "EMA50" in df.columns
                else np.nan
            )

            rsi = (
                df["RSI"].iloc[i]
                if "RSI" in df.columns
                else np.nan
            )

            buy_setup = False
            sell_setup = False

            # -------------------------------------------------
            # Trend setup
            # -------------------------------------------------

            if ( 
                not pd.isna(ema20) 
                and not pd.isna(ema50) 
                ): 

                if close > ema20 > ema50:
                     buy_setup = True 
                     df.iloc[
                      i,
                       df.columns.get_loc("SETUP_DIRECTION")
                         ] = "BUY"

                     
                elif close < ema20 < ema50: 
                     sell_setup = True 
                     df.iloc[ i,
                              df.columns.get_loc("SETUP_DIRECTION")
                              ] = "SELL"

            # -------------------------------------------------
            # RSI filter
            # -------------------------------------------------

            if not pd.isna(rsi):

                if rsi >= 70:
                    buy_setup = False

                if rsi <= 30:
                    sell_setup = False

            # -------------------------------------------------
            # No setup -> HOLD
            # -------------------------------------------------

            if not buy_setup and not sell_setup:

                LabelBuilder._set_result(
                    df=df,
                    index=i,
                    label=1,
                    direction="NONE",
                    trade_return=0.0,
                    holding_period=0,
                    exit_reason="NO_TRADE",
                )

                continue

            # -------------------------------------------------
            # Both setups -> HOLD
            #
            # This should normally never happen because the
            # EMA conditions are mutually exclusive.
            # -------------------------------------------------

            if buy_setup and sell_setup:

                LabelBuilder._set_result(
                    df=df,
                    index=i,
                    label=1,
                    direction="NONE",
                    trade_return=0.0,
                    holding_period=0,
                    exit_reason="AMBIGUOUS_SETUP",
                )

                continue

            # =================================================
            # BUY SETUP
            # =================================================

            if buy_setup:

                result = LabelBuilder._simulate_trade(
                    df=df,
                    entry_index=entry_index,
                    entry=entry,
                    stop=buy_sl,
                    target=buy_target,
                    direction="BUY",
                )

                # -------------------------------------------------
                # IMPORTANT:
                #
                # A BUY setup that loses is HOLD, NOT SELL.
                #
                # Future outcome decides whether the pre-selected
                # BUY setup deserves label BUY or HOLD.
                # It must never turn into the opposite direction.
                # -------------------------------------------------

                if result["return"] > LabelBuilder.MIN_EDGE:
                    label = 2
                    direction = "BUY"
                else:
                    label = 1
                    direction = "NONE"

                LabelBuilder._set_result(
                    df=df,
                    index=i,
                    label=label,
                    direction=direction,
                    trade_return=result["return"],
                    holding_period=result["holding_period"],
                    exit_reason=result["exit_reason"],
                )

                continue

            # =================================================
            # SELL SETUP
            # =================================================

            if sell_setup:

                result = LabelBuilder._simulate_trade(
                    df=df,
                    entry_index=entry_index,
                    entry=entry,
                    stop=sell_sl,
                    target=sell_target,
                    direction="SELL",
                )

                # -------------------------------------------------
                # IMPORTANT:
                #
                # A SELL setup that loses is HOLD, NOT BUY.
                # -------------------------------------------------

                if result["return"] > LabelBuilder.MIN_EDGE:
                    label = 0
                    direction = "SELL"
                else:
                    label = 1
                    direction = "NONE"

                LabelBuilder._set_result(
                    df=df,
                    index=i,
                    label=label,
                    direction=direction,
                    trade_return=result["return"],
                    holding_period=result["holding_period"],
                    exit_reason=result["exit_reason"],
                )

        # -----------------------------------------------------
        # Enforce final data types.
        # -----------------------------------------------------

        df["LABEL"] = (
            pd.to_numeric(
                df["LABEL"],
                errors="coerce",
            )
            .fillna(1)
            .astype(int)
        )

        df["TRADE_DIRECTION"] = (
            df["TRADE_DIRECTION"]
            .fillna("NONE")
            .astype(str)
        )

        df["TRADE_RETURN"] = (
            pd.to_numeric(
                df["TRADE_RETURN"],
                errors="coerce",
            )
            .fillna(0.0)
            .astype(float)
        )

        df["HOLDING_PERIOD"] = (
            pd.to_numeric(
                df["HOLDING_PERIOD"],
                errors="coerce",
            )
            .fillna(0)
            .astype(int)
        )

        df["EXIT_REASON"] = (
            df["EXIT_REASON"]
            .fillna("NO_TRADE")
            .astype(str)
        )

        # -----------------------------------------------------
        # FINAL INVARIANT
        #
        # This is the critical fix.
        # -----------------------------------------------------

        df.loc[
            df["LABEL"] == 0,
            "TRADE_DIRECTION"
        ] = "SELL"

        df.loc[
            df["LABEL"] == 1,
            "TRADE_DIRECTION"
        ] = "NONE"

        df.loc[
            df["LABEL"] == 2,
            "TRADE_DIRECTION"
        ] = "BUY"

        return df

    # =========================================================
    # SET RESULT
    # =========================================================

    @staticmethod
    def _set_result(
        df,
        index,
        label,
        direction,
        trade_return,
        holding_period,
        exit_reason,
    ):

        df.iloc[
            index,
            df.columns.get_loc("LABEL")
        ] = int(label)

        df.iloc[
            index,
            df.columns.get_loc("TRADE_DIRECTION")
        ] = direction

        df.iloc[
            index,
            df.columns.get_loc("TRADE_RETURN")
        ] = float(trade_return)

        df.iloc[
            index,
            df.columns.get_loc("HOLDING_PERIOD")
        ] = int(holding_period)

        df.iloc[
            index,
            df.columns.get_loc("EXIT_REASON")
        ] = exit_reason

    # =========================================================
    # TRADE SIMULATOR
    # =========================================================

    @staticmethod
    def _simulate_trade(
        df,
        entry_index,
        entry,
        stop,
        target,
        direction,
    ):
        """
        Simulates one already-selected BUY or SELL setup.

        Conservative assumption:
        if STOP and TARGET are both touched inside the same
        candle, STOP is assumed to happen first.
        """

        last_index = min(
            len(df) - 1,
            entry_index
            + LabelBuilder.MAX_HOLDING_PERIOD
            - 1,
        )

        for j in range(
            entry_index,
            last_index + 1,
        ):

            high = float(
                df["High"].iloc[j]
            )

            low = float(
                df["Low"].iloc[j]
            )

            if (
                not np.isfinite(high)
                or not np.isfinite(low)
            ):
                continue

            # =================================================
            # BUY
            # =================================================

            if direction == "BUY":

                stop_hit = low <= stop
                target_hit = high >= target

                # -------------------------------------------------
                # Both touched:
                # conservative assumption = STOP first.
                # -------------------------------------------------

                if stop_hit and target_hit:

                    exit_price = stop

                    gross_return = (
                        exit_price - entry
                    ) / entry

                    net_return = (
                        gross_return
                        - LabelBuilder.ROUND_TRIP_COST
                    )

                    return {
                        "return": float(net_return),
                        "holding_period": (
                            j - entry_index + 1
                        ),
                        "exit_reason": "STOP",
                    }

                # -------------------------------------------------
                # STOP
                # -------------------------------------------------

                if stop_hit:

                    exit_price = stop

                    gross_return = (
                        exit_price - entry
                    ) / entry

                    net_return = (
                        gross_return
                        - LabelBuilder.ROUND_TRIP_COST
                    )

                    return {
                        "return": float(net_return),
                        "holding_period": (
                            j - entry_index + 1
                        ),
                        "exit_reason": "STOP",
                    }

                # -------------------------------------------------
                # TARGET
                # -------------------------------------------------

                if target_hit:

                    exit_price = target

                    gross_return = (
                        exit_price - entry
                    ) / entry

                    net_return = (
                        gross_return
                        - LabelBuilder.ROUND_TRIP_COST
                    )

                    return {
                        "return": float(net_return),
                        "holding_period": (
                            j - entry_index + 1
                        ),
                        "exit_reason": "TARGET",
                    }

            # =================================================
            # SELL
            # =================================================

            elif direction == "SELL":

                stop_hit = high >= stop
                target_hit = low <= target

                # -------------------------------------------------
                # Both touched:
                # conservative assumption = STOP first.
                # -------------------------------------------------

                if stop_hit and target_hit:

                    exit_price = stop

                    gross_return = (
                        entry - exit_price
                    ) / entry

                    net_return = (
                        gross_return
                        - LabelBuilder.ROUND_TRIP_COST
                    )

                    return {
                        "return": float(net_return),
                        "holding_period": (
                            j - entry_index + 1
                        ),
                        "exit_reason": "STOP",
                    }

                # -------------------------------------------------
                # STOP
                # -------------------------------------------------

                if stop_hit:

                    exit_price = stop

                    gross_return = (
                        entry - exit_price
                    ) / entry

                    net_return = (
                        gross_return
                        - LabelBuilder.ROUND_TRIP_COST
                    )

                    return {
                        "return": float(net_return),
                        "holding_period": (
                            j - entry_index + 1
                        ),
                        "exit_reason": "STOP",
                    }

                # -------------------------------------------------
                # TARGET
                # -------------------------------------------------

                if target_hit:

                    exit_price = target

                    gross_return = (
                        entry - exit_price
                    ) / entry

                    net_return = (
                        gross_return
                        - LabelBuilder.ROUND_TRIP_COST
                    )

                    return {
                        "return": float(net_return),
                        "holding_period": (
                            j - entry_index + 1
                        ),
                        "exit_reason": "TARGET",
                    }

            else:

                raise ValueError(
                    f"Invalid trade direction: {direction}"
                )

        # =====================================================
        # TIME EXIT
        # =====================================================

        exit_price = float(
            df["Close"].iloc[last_index]
        )

        if not np.isfinite(exit_price):
            exit_price = entry

        if direction == "BUY":

            gross_return = (
                exit_price - entry
            ) / entry

        else:

            gross_return = (
                entry - exit_price
            ) / entry

        net_return = (
            gross_return
            - LabelBuilder.ROUND_TRIP_COST
        )

        return {
            "return": float(net_return),
            "holding_period": (
                last_index - entry_index + 1
            ),
            "exit_reason": "TIME",
        }