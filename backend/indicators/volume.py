import ta


def calculate(df):

    df["OBV"] = ta.volume.on_balance_volume(
        df["Close"],
        df["Volume"]
    )

    df["CMF"] = ta.volume.chaikin_money_flow(
        df["High"],
        df["Low"],
        df["Close"],
        df["Volume"]
    )

    return df