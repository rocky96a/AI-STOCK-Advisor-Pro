from flask import Blueprint, jsonify, request

from backend.services.yahoo_service import YahooService
from backend.services import scanner_service

from backend.agents.technical_agent import TechnicalAgent
from backend.agents.news_agent import NewsAgent

from backend.algo.strategy_manager import StrategyManager

from backend.decision.decision_engine import DecisionEngine
from backend.data.data_engine import DataEngine
from backend.data.symbol_utils import normalize_symbol

from backend.ai.confidence_engine import ConfidenceEngine

from backend.ml.predict import Predictor
from backend.ml.train import train_model
from backend.ml.dataset import DatasetBuilder
from backend.ml.model_manager import ModelManager
from backend.ml.xgboost_model import XGBoostTrainer

from backend.backtest.backtester import BackTester

from backend.auth.decorators import token_required


# ==========================================================
# BLUEPRINT
# ==========================================================

api = Blueprint("api", __name__)


# ==========================================================
# DATA ENGINE
# ==========================================================

data_engine = DataEngine()


# ==========================================================
# STOCK INFORMATION API
# ==========================================================

@api.route("/stock/<symbol>")
@token_required
def stock(symbol):

    symbol = normalize_symbol(symbol)

    data = YahooService.get_stock(symbol)

    if data is None:

        return jsonify({
            "success": False,
            "message": "Stock not found"
        }), 404

    response = data.copy()

    # DataFrame cannot be returned directly as JSON.
    response.pop("df", None)

    return jsonify(response)


# ==========================================================
# TECHNICAL ANALYSIS API
# ==========================================================

@api.route("/analyze/<symbol>")
@token_required
def analyze(symbol):

    symbol = normalize_symbol(symbol)

    interval = request.args.get("interval", "1d")
    period = request.args.get("period")

    stock = YahooService.get_stock(
        symbol,
        interval=interval,
        period=period,
    )

    if stock is None:

        return jsonify({
            "success": False,
            "message": "Stock not found"
        }), 404

    analysis = TechnicalAgent.analyze(
        stock["df"]
    )

    return jsonify({

        "company": stock["company"],
        "symbol": stock["symbol"],
        "interval": interval,
        "price": stock["price"],
        "sector": stock["sector"],
        "industry": stock["industry"],
        "marketCap": stock["marketCap"],
        "history": stock["history"],
        "analysis": analysis

    })


# ==========================================================
# CHART API
# ==========================================================

@api.route("/chart/<symbol>")
@token_required
def chart(symbol):

    symbol = normalize_symbol(symbol)

    interval = request.args.get(
        "interval",
        "1d"
    )

    period = request.args.get(
        "period"
    )

    stock = YahooService.get_stock(

        symbol=symbol,
        interval=interval,
        period=period

    )

    if stock is None:

        return jsonify({
            "success": False,
            "message": "Chart not available"
        }), 404

    return jsonify({

        "candles": stock["history"],
        "volume": stock["volume"],
        "ema20": stock["ema20"],
        "ema50": stock["ema50"],
        "sma200": stock["sma200"],
        "rsi": stock["rsi"]

    })


# ==========================================================
# AI / FINAL PREDICTION API
# ==========================================================

@api.route("/predict/<symbol>")
@token_required
def predict(symbol):

    symbol = normalize_symbol(symbol)

    # ======================================================
    # SELECTED TIMEFRAME
    #
    # Previously this always analyzed the daily candle regardless of
    # what timeframe the chart was showing, so the verdict/indicators
    # never reflected a 5m/15m view. Now the same indicator pipeline
    # (TechnicalAgent, StrategyManager, ConfidenceEngine) runs on
    # whatever interval the chart/dashboard asks for.
    # ======================================================

    interval = request.args.get("interval", "1d")
    period = request.args.get("period")

    # ======================================================
    # MAIN STOCK DATA
    # ======================================================

    stock = YahooService.get_stock(
        symbol,
        interval=interval,
        period=period,
    )

    if stock is None:

        return jsonify({
            "success": False,
            "message": "Stock not found"
        }), 404

    df = stock["df"]

    print(
        f"[Predict] {symbol}: "
        f"interval={interval} "
        f"YahooService dataframe rows="
        f"{len(df)}"
    )

    print(
        f"[Predict] {symbol}: "
        f"first="
        f"{df.index[0] if not df.empty else None}"
    )

    print(
        f"[Predict] {symbol}: "
        f"last="
        f"{df.index[-1] if not df.empty else None}"
    )


    # ======================================================
    # TECHNICAL ANALYSIS
    # ======================================================

    technical = TechnicalAgent.analyze(
        df
    )


    # ======================================================
    # MACHINE LEARNING
    # ======================================================

    ml_result = Predictor.predict(
        df,
        symbol=symbol,
    )


    # ======================================================
    # ALGORITHMIC STRATEGIES
    # ======================================================

    algo_result = StrategyManager.analyze(
        df
    )


    # ======================================================
    # NEWS
    # ======================================================

    news = NewsAgent.analyze(
        symbol=symbol,
        company_name=stock.get("company"),
    )


    # ======================================================
    # AI CONFIDENCE ENGINE
    # ======================================================

    ai_result = ConfidenceEngine.calculate(

        technical=technical,

        ml=ml_result,

        algorithmic=algo_result,

        news=news["sentiment"]

    )


    # ======================================================
    # MULTI-TIMEFRAME DATA
    #
    # 1D  = Daily
    # 1H  = Hourly
    # 15M = Intraday
    # ======================================================

    try:

        dataframes = (
            data_engine.load_multiple_timeframes(

                symbol=symbol,

                intervals=[
                    "1d",
                    "1h",
                    "15m",
                ],

                auto_download=True,
            )
        )

    except Exception as exc:

        print(
            f"[Predict] {symbol}: "
            f"MTF loading failed: {exc}"
        )

        dataframes = {
            "1d": None,
            "1h": None,
            "15m": None,
        }


    # ======================================================
    # MTF DATA STATUS
    # ======================================================

    mtf_status = {}

    for interval, timeframe_df in dataframes.items():

        mtf_status[interval] = (
            timeframe_df is not None
            and not timeframe_df.empty
        )

    print(
        f"[Predict] {symbol}: "
        f"MTF status={mtf_status}"
    )


    # ======================================================
    # FINAL DECISION ENGINE
    #
    # This is now the ONLY final decision engine.
    #
    # ML
    # Technical
    # Multi-Timeframe
    # Contradiction checks
    # Safety checks
    # Confidence
    # ======================================================

    decision = DecisionEngine.analyze(

        df,

        symbol,

        dataframes=dataframes,

    )


    # ======================================================
    # FINAL RESPONSE
    # ======================================================

    return jsonify({

        "symbol": symbol,

        "interval": interval,

        "company": stock["company"],

        "price": stock["price"],

        "technical": technical,

        "ml": ml_result,

        "algorithmic": algo_result,

        "news": news,

        "ai": ai_result,

        "decision": decision,

    })


# ==========================================================
# MARKET SCANNER API
# ==========================================================

@api.route("/scan")
@token_required
def scan():

    top_n = int(
        request.args.get(
            "top",
            10
        )
    )

    with_ml = (
        request.args.get(
            "ml",
            "false"
        ).lower()
        == "true"
    )

    results = scanner_service.scan(

        top_n=top_n,

        enrich_with_ml=with_ml

    )

    return jsonify({

        "count": len(results),

        "results": results

    })


# ==========================================================
# ML DATASET API
# ==========================================================

@api.route("/dataset/<symbol>")
@token_required
def dataset(symbol):

    symbol = normalize_symbol(symbol)

    try:

        builder = DatasetBuilder()

        df = builder.create(
            symbol
        )

        if df is None or df.empty:

            return jsonify({

                "success": False,

                "message": "Dataset unavailable"

            }), 404

        return jsonify({

            "success": True,

            "rows": len(df),

            "data": (
                df.tail(100)
                .to_dict("records")
            )

        })

    except Exception as exc:

        return jsonify({

            "success": False,

            "error": str(exc)

        }), 500


# ==========================================================
# TRAIN ML MODEL API
# ==========================================================

@api.route("/train/<symbol>")
@token_required
def train(symbol):

    symbol = normalize_symbol(symbol)

    try:

        result = train_model(
            symbol
        )

        return jsonify(
            result
        )

    except Exception as exc:

        return jsonify({

            "success": False,

            "error": str(exc)

        }), 500


# ==========================================================
# LIST ML MODELS API
# ==========================================================

@api.route("/models")
@token_required
def models():

    manager = ModelManager()

    return jsonify(
        manager.list_models()
    )


# ==========================================================
# TRAIN XGBOOST MODEL
# ==========================================================

@api.route("/train/xgboost/<symbol>")
@token_required
def train_xgboost(symbol):

    symbol = normalize_symbol(symbol)

    result = XGBoostTrainer.train(
        symbol
    )

    return jsonify(
        result
    )


# ==========================================================
# TRAIN LSTM MODEL
# ==========================================================

@api.route("/train/lstm/<symbol>")
@token_required
def train_lstm(symbol):

    symbol = normalize_symbol(symbol)

    from backend.ml.lstm_model import (
        LSTMTrainer
    )

    builder = DatasetBuilder()

    X, y = builder.get_features(
        symbol
    )

    result = LSTMTrainer.train(
        X,
        y
    )

    return jsonify(
        result
    )


# ==========================================================
# BACKTEST API
# ==========================================================

@api.route("/backtest/<symbol>")
@token_required
def backtest(symbol):

    symbol = normalize_symbol(symbol)

    stock = YahooService.get_stock(
        symbol
    )

    if stock is None:

        return jsonify({
            "success": False
        }), 404

    tester = BackTester()

    result = tester.run(

        stock["df"],

        predictor="ensemble"

    )

    return jsonify(
        result
    )