import ta


def calculate(df):

    df["EMA9"] = ta.trend.ema_indicator(df["Close"], window=9)

    df["EMA20"] = ta.trend.ema_indicator(df["Close"], window=20)

    df["EMA50"] = ta.trend.ema_indicator(df["Close"], window=50)

    df["EMA100"] = ta.trend.ema_indicator(df["Close"], window=100)

    df["EMA200"] = ta.trend.ema_indicator(df["Close"], window=200)

    df["SMA200"] = ta.trend.sma_indicator(df["Close"], window=200)

    return df