"""
Turns an indicator-enriched OHLCV dataframe into an (X, y) training
set for the ML agent.

Label definition (kept simple and honest):
  For each row, look `horizon` candles ahead. If the close moved up
  by more than `atr_threshold` x that row's ATR, label = 1 (UP).
  If it moved down by more than that, label = 0 (DOWN).
  Anything in between (chop / no clear move) is dropped from
  training so the model isn't forced to guess on noise.

This is a classification problem: "will there be a clean move up or
down in the next N candles?" — not a price forecast. That's a much
more honest and learnable target than trying to predict exact price.
"""

import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "RSI", "MACD", "MACD_SIGNAL", "ADX", "CCI",
    "EMA9", "EMA20", "EMA50", "EMA100", "EMA200",
    "ATR", "CMF", "OBV",
]


def build_features(df):
    """
    Assumes df already has all indicator columns computed
    (trend, momentum, volatility, volume modules have run).
    Adds a few derived, scale-independent features and returns
    only the feature columns (still indexed like df).
    """
    feat = pd.DataFrame(index=df.index)

    price = df["Close"]

    feat["rsi"] = df["RSI"]
    feat["macd_hist"] = df["MACD"] - df["MACD_SIGNAL"]
    feat["adx"] = df["ADX"]
    feat["cci"] = df["CCI"]

    # Express EMAs as % distance from price so the model generalizes
    # across stocks with very different price levels (₹50 vs ₹5000).
    for span in ["EMA9", "EMA20", "EMA50", "EMA100", "EMA200"]:
        feat[f"{span.lower()}_pct"] = (price - df[span]) / price * 100

    feat["atr_pct"] = df["ATR"] / price * 100
    feat["cmf"] = df["CMF"]

    # OBV slope over the last 5 candles (direction of money flow),
    # normalized so raw OBV magnitude doesn't dominate.
    obv_slope = df["OBV"].diff(5)
    feat["obv_slope_norm"] = obv_slope / (df["Volume"].rolling(5).mean() * 5 + 1e-9)

    # Recent momentum: % change over last 3 and 10 candles
    feat["ret_3"] = price.pct_change(3) * 100
    feat["ret_10"] = price.pct_change(10) * 100

    return feat


def build_labels(df, horizon=5, atr_threshold=1.0):
    """
    horizon: how many candles ahead to look
    atr_threshold: how many ATRs of favorable move counts as a
        clean UP/DOWN label (below this = chop, excluded)
    """
    price = df["Close"]
    atr = df["ATR"]

    future_price = price.shift(-horizon)
    move = future_price - price
    move_in_atr = move / atr.replace(0, np.nan)

    labels = pd.Series(np.nan, index=df.index)
    labels[move_in_atr >= atr_threshold] = 1
    labels[move_in_atr <= -atr_threshold] = 0

    return labels


def build_training_set(df, horizon=5, atr_threshold=1.0):
    """
    Returns (X, y) with rows containing NaN features/labels dropped,
    and the last row of X (today's, unlabeled since the future is
    unknown yet) returned separately for live prediction.
    """
    features = build_features(df)
    labels = build_labels(df, horizon=horizon, atr_threshold=atr_threshold)

    combined = features.copy()
    combined["__label__"] = labels

    live_row = features.iloc[[-1]]  # most recent candle, to predict on

    # Drop the tail `horizon` rows (label unknown) and any NaNs from
    # indicator warm-up periods, for training.
    trainable = combined.iloc[:-horizon].dropna()

    X = trainable.drop(columns="__label__")
    y = trainable["__label__"].astype(int)

    return X, y, live_row
