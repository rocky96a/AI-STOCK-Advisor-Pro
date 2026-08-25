import ta


def calculate(df):

    bb = ta.volatility.BollingerBands(df["Close"])

    df["BB_UPPER"] = bb.bollinger_hband()

    df["BB_LOWER"] = bb.bollinger_lband()

    df["ATR"] = ta.volatility.average_true_range(
        df["High"],
        df["Low"],
        df["Close"]
    )

    return df