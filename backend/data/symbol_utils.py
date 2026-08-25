"""Canonical Yahoo Finance symbol normalization."""

INDEX_SYMBOLS = {
    # India
    "NIFTY 50": "^NSEI",
    "NIFTY50": "^NSEI",
    "NIFTY": "^NSEI",
    "SENSEX": "^BSESN",
    "BANK NIFTY": "^NSEBANK",
    "BANKNIFTY": "^NSEBANK",

    # USA
    "S&P 500": "^GSPC",
    "S&P500": "^GSPC",
    "SP500": "^GSPC",
    "NASDAQ": "^IXIC",
    "NASDAQ COMPOSITE": "^IXIC",
    "DOW": "^DJI",
    "DOW JONES": "^DJI",
}

GLOBAL_SYMBOLS = {
    # US stocks
    "TESLA": "TSLA",
    "TSLA": "TSLA",

    "APPLE": "AAPL",
    "AAPL": "AAPL",

    "MICROSOFT": "MSFT",
    "MSFT": "MSFT",

    "NVIDIA": "NVDA",
    "NVDA": "NVDA",

    "AMAZON": "AMZN",
    "AMZN": "AMZN",

    "META": "META",

    "GOOGLE": "GOOGL",
    "GOOGL": "GOOGL",

    "NETFLIX": "NFLX",
    "NFLX": "NFLX",

    "AMD": "AMD",

    "TSM": "TSM",
    "TAIWAN SEMICONDUCTOR": "TSM",

    # Crypto
    "BITCOIN": "BTC-USD",
    "BTC": "BTC-USD",
    "BTC-USD": "BTC-USD",

    "ETHEREUM": "ETH-USD",
    "ETH": "ETH-USD",
    "ETH-USD": "ETH-USD",
}


def normalize_symbol(symbol):
    """Return the canonical Yahoo Finance symbol."""

    if symbol is None:
        return None

    value = str(symbol).strip().upper()

    if not value:
        return None

    # Already Yahoo index
    if value.startswith("^"):
        return value

    # Friendly indices
    if value in INDEX_SYMBOLS:
        return INDEX_SYMBOLS[value]

    # Global stocks / crypto
    if value in GLOBAL_SYMBOLS:
        return GLOBAL_SYMBOLS[value]

    # Already exchange-qualified
    if value.endswith((".NS", ".BO", "-USD", "=X")):
        return value

    # Default to NSE for unknown stock symbols
    return f"{value}.NS"
