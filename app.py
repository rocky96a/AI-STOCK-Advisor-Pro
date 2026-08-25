from flask import Flask, render_template, jsonify, request

import yfinance as yf
import pandas as pd

from backend.services.scanner_service import scan, scan_recommendations
from backend.api.routes import api
from backend.services.yahoo_service import YahooService
from backend.agents.technical_agent import TechnicalAgent
from backend.portfolio.portfolio_manager import PortfolioManager

from backend.auth import user_store
from backend.auth.routes import auth_api
from backend.auth.decorators import token_required

from backend.data.cache import cache_get, cache_set, TTL_MARKET_BAR

app = Flask(__name__)

# Seed/open the users DB on startup (creates backend/data/users.db and a
# default admin account the first time this runs).
user_store.init_db()

# =====================================
# Register API Blueprints
# =====================================

app.register_blueprint(api, url_prefix="/api")
app.register_blueprint(auth_api, url_prefix="/api/auth")


# =====================================
# HOME
# =====================================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/ai-signals")
def ai_signals_page():
    return render_template("ai_signals.html")


@app.route("/ai-chat")
def ai_chat_page():
    return render_template("chat.html")


# =====================================
# LOGIN PAGE (never gated - this is the door in)
# =====================================

@app.route("/login")
def login_page():
    return render_template("login.html")


# =====================================
# TEST
# =====================================

@app.route("/test")
@token_required
def test():

    stock = YahooService.get_stock("RELIANCE.NS")

    if stock is None:
        return {"error": "Unable to fetch stock data"}

    result = TechnicalAgent.analyze(stock["df"])

    return result


# =====================================
# PORTFOLIO API
# File: app.py
# =====================================

# =====================================
# PORTFOLIO API
# =====================================

portfolio_manager = PortfolioManager(initial_cash=100000.0)


@app.route("/api/portfolio", methods=["GET"])
@token_required
def portfolio_api():
    return jsonify(portfolio_manager.summary())


@app.route("/api/portfolio/positions", methods=["POST"])
@token_required
def add_portfolio_position():
    try:
        payload = request.get_json(silent=True) or {}
        symbol = str(payload.get("symbol", "")).strip().upper()
        quantity = payload.get("quantity")
        entry_price = payload.get("entry_price", payload.get("entry"))

        if not symbol or quantity is None or entry_price is None:
            return jsonify({
                "success": False,
                "error": "symbol, quantity and entry_price are required",
            }), 400

        position = portfolio_manager.add_position(
            symbol=symbol,
            quantity=quantity,
            entry_price=entry_price,
        )

        return jsonify({
            "success": True,
            "position": position.to_dict(),
            "portfolio": portfolio_manager.summary(),
        }), 201

    except (TypeError, ValueError) as exc:
        return jsonify({
            "success": False,
            "error": str(exc),
        }), 400


@app.route("/api/portfolio/positions/<symbol>", methods=["DELETE"])
@token_required
def remove_portfolio_position(symbol):
    portfolio_manager.remove_position(symbol)
    return jsonify({
        "success": True,
        "portfolio": portfolio_manager.summary(),
    })


@app.route("/api/portfolio/positions/<symbol>/price", methods=["PATCH"])
@token_required
def update_portfolio_price(symbol):
    try:
        payload = request.get_json(silent=True) or {}
        current_price = payload.get("current_price", payload.get("price"))

        if current_price is None:
            return jsonify({
                "success": False,
                "error": "current_price is required",
            }), 400

        position = portfolio_manager.update_price(
            symbol,
            current_price,
        )

        if position is None:
            return jsonify({
                "success": False,
                "error": f"Position not found: {symbol}",
            }), 404

        return jsonify({
            "success": True,
            "position": position.to_dict(),
            "portfolio": portfolio_manager.summary(),
        })

    except (TypeError, ValueError) as exc:
        return jsonify({
            "success": False,
            "error": str(exc),
        }), 400


@app.route("/api/recommendations")
@token_required
def recommendations_api():
    """
    Today's AI picks: top BUY and top SELL candidates, ranked by the
    same safety-score system used elsewhere (confidence + risk:reward,
    penalized for wide stop-losses). Backs the "Today's Top Picks"
    panel on the dashboard.

    Query params:
        buy   - how many BUY ideas to return (default 10)
        sell  - how many SELL ideas to return (default 10)
        ml    - "true" to enrich the shortlist with ML predictions
    """

    buy_n = int(request.args.get("buy", 10))
    sell_n = int(request.args.get("sell", 10))
    with_ml = request.args.get("ml", "false").lower() == "true"

    try:
        data = scan_recommendations(
            buy_n=buy_n,
            sell_n=sell_n,
            enrich_with_ml=with_ml,
        )

        return jsonify({
            "success": True,
            **data,
        })

    except Exception as error:
        print("RECOMMENDATIONS ERROR:", error)

        return jsonify({
            "success": False,
            "buy": [],
            "sell": [],
            "error": str(error),
        }), 500


@app.route("/api/watchlist")
@token_required
def watchlist_api():

    try:

        results = scan(
            top_n=10,
            enrich_with_ml=False
        )

        return jsonify({
            "success": True,
            "count": len(results),
            "stocks": results
        })

    except Exception as error:

        print("WATCHLIST ERROR:", error)

        return jsonify({
            "success": False,
            "count": 0,
            "stocks": [],
            "error": str(error)
        }), 500
# =====================================
# MARKET BAR API
# =====================================

@app.route("/api/market")
@token_required
def market_api():
    """Fetch a compact live market snapshot for the dashboard bar.

    Cached for TTL_MARKET_BAR seconds — this bar polls in the background,
    and without caching every poll was re-downloading 13 tickers from
    Yahoo Finance from scratch.
    """

    cache_key = ("market_bar",)
    cached_payload = cache_get(cache_key)
    if cached_payload is not None:
        return jsonify(cached_payload)

    symbols = {
        # Indian market
        "nifty": "^NSEI",
        "bank_nifty": "^NSEBANK",
        "sensex": "^BSESN",

        # Global indices
        "sp500": "^GSPC",
        "nasdaq": "^IXIC",
        "dow": "^DJI",

        # Global stock
        "tesla": "TSLA",

        # Forex / commodities
        "usd_inr": "INR=X",
        "gold": "GC=F",
        "crude": "CL=F",

        # Crypto
        "btc": "BTC-USD",
        "eth": "ETH-USD",
    }

    try:
        raw = yf.download(
            list(symbols.values()),
            period="5d",
            interval="1d",
            progress=False,
            auto_adjust=False,
            threads=True,
            group_by="column",
        )

        if raw is None or raw.empty:
            raise RuntimeError("No market data returned")

        close = raw["Close"] if "Close" in raw else pd.DataFrame()
        result = {}

        for key, ticker in symbols.items():
            try:
                series = close[ticker].dropna()
                if len(series) == 0:
                    continue

                current = float(series.iloc[-1])
                previous = float(series.iloc[-2]) if len(series) > 1 else current
                change_pct = (
                    ((current - previous) / previous) * 100
                    if previous
                    else 0.0
                )

                result[key] = {
                    "symbol": ticker,
                    "price": round(current, 2),
                    "change_percent": round(change_pct, 2),
                    "direction": "UP" if change_pct > 0 else (
                        "DOWN" if change_pct < 0 else "FLAT"
                    ),
                }
            except Exception as exc:
                print(f"[Market] {ticker}: {exc}")

        payload = {
            "success": True,
            "data": result,
        }

        cache_set(cache_key, payload, ttl=TTL_MARKET_BAR)

        return jsonify(payload)

    except Exception as exc:
        print("[Market] ERROR:", exc)
        return jsonify({
            "success": False,
            "data": {},
            "error": str(exc),
        }), 503


# =====================================
# RISK API
# =====================================

@app.route("/api/risk")
@token_required
def risk_api():
    """Return calculated session portfolio risk metrics.

    `portfolio_risk` is exposure as a percentage of current equity, not a
    claim of statistical loss probability. Max drawdown is tracked from the
    portfolio manager's session equity history.
    """

    summary = portfolio_manager.summary()

    total_value = float(summary.get("total_value", 0.0) or 0.0)
    invested = float(summary.get("invested", 0.0) or 0.0)

    exposure = (
        (invested / total_value) * 100
        if total_value > 0
        else 0.0
    )

    if exposure >= 90:
        risk_level = "HIGH"
    elif exposure >= 60:
        risk_level = "MODERATE"
    else:
        risk_level = "LOW"

    return jsonify({
        "portfolio_risk": round(exposure, 2),
        "exposure_percent": round(exposure, 2),
        "risk_level": risk_level,
        "max_drawdown": summary.get("max_drawdown_percent", 0.0),
        "max_drawdown_value": summary.get("max_drawdown_value", 0.0),
        "risk_reward": None,
        "open_positions": summary.get("open_positions", 0),
        "total_value": total_value,
        "invested": invested,
        "available_cash": summary.get("available_cash", 0.0),
        "total_pnl": summary.get("total_pnl", 0.0),
    })



@app.route("/watchlist")
def watchlist():
    return render_template("watchlist.html")


@app.route("/portfolio")
def portfolio():
    return render_template("portfolio.html")


# =====================================
# START SERVER
# =====================================

if __name__ == "__main__":
    import os

    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    port = int(os.environ.get("PORT", 5000))

    app.run(host="0.0.0.0", port=port, debug=debug_mode)

