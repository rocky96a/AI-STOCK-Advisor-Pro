import ta


def calculate(df):

    df["RSI"] = ta.momentum.rsi(df["Close"])

    df["MACD"] = ta.trend.macd(df["Close"])

    df["MACD_SIGNAL"] = ta.trend.macd_signal(df["Close"])

    df["ADX"] = ta.trend.adx(
        df["High"],
        df["Low"],
        df["Close"]
    )

    df["CCI"] = ta.trend.cci(
        df["High"],
        df["Low"],
        df["Close"]
    )

    return df