// Canonical Yahoo Finance symbol normalization.

const INDEX_SYMBOLS = Object.freeze({
    "NIFTY 50": "^NSEI",
    "NIFTY50": "^NSEI",
    "NIFTY": "^NSEI",

    "SENSEX": "^BSESN",

    "BANK NIFTY": "^NSEBANK",
    "BANKNIFTY": "^NSEBANK",

    "S&P 500": "^GSPC",
    "S&P500": "^GSPC",
    "SP500": "^GSPC",

    "NASDAQ": "^IXIC",
    "NASDAQ COMPOSITE": "^IXIC",

    "DOW": "^DJI",
    "DOW JONES": "^DJI"
});

const GLOBAL_SYMBOLS = Object.freeze({
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

    "BITCOIN": "BTC-USD",
    "BTC": "BTC-USD",
    "BTC-USD": "BTC-USD",

    "ETHEREUM": "ETH-USD",
    "ETH": "ETH-USD",
    "ETH-USD": "ETH-USD"
});

function normalizeStockSymbol(value) {

    let symbol =
        String(value || "RELIANCE")
            .trim()
            .toUpperCase();

    if (!symbol) {
        return "RELIANCE.NS";
    }

    if (symbol.startsWith("^")) {
        return symbol;
    }

    if (
        Object.prototype.hasOwnProperty.call(
            INDEX_SYMBOLS,
            symbol
        )
    ) {
        return INDEX_SYMBOLS[symbol];
    }

    if (
        Object.prototype.hasOwnProperty.call(
            GLOBAL_SYMBOLS,
            symbol
        )
    ) {
        return GLOBAL_SYMBOLS[symbol];
    }

    if (
        symbol.endsWith(".NS") ||
        symbol.endsWith(".BO") ||
        symbol.endsWith("-USD") ||
        symbol.endsWith("=X")
    ) {
        return symbol;
    }

    return `${symbol}.NS`;
}

function displayStockSymbol(symbol) {

    const value =
        String(symbol || "")
            .trim()
            .toUpperCase();

    const labels = {
        "^NSEI": "NIFTY 50",
        "^BSESN": "SENSEX",
        "^NSEBANK": "BANK NIFTY",
        "^GSPC": "S&P 500",
        "^IXIC": "NASDAQ",
        "^DJI": "DOW JONES",
        "BTC-USD": "BITCOIN",
        "ETH-USD": "ETHEREUM"
    };

    if (labels[value]) {
        return labels[value];
    }

    return value
        .replace(/\.NS$/i, "")
        .replace(/\.BO$/i, "");
}
