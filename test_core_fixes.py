from backend.ai.confidence_engine import ConfidenceEngine
from backend.news.moneycontrol_service import MoneyControlService
from backend.portfolio.portfolio_manager import PortfolioManager


def test_confidence_never_calls_28_percent_strong_buy():
    result = ConfidenceEngine.calculate(
        technical={"signal": "BUY", "confidence": 60, "strength": "MODERATE"},
        ml={"available": False},
        algorithmic={"signal": "HOLD", "confidence": 65},
        news={"sentiment": "Neutral", "confidence": 90},
    )
    assert result["recommendation"] == "BUY"
    assert result["confidence"] < 65


def test_moneycontrol_parser_rejects_navigation():
    html = """
    <ul>
      <li><a href="/news/business/stocks/real-headline.html">
        <h2>Infosys profit rises as growth improves</h2>
      </a><p>Company reported stronger results.</p></li>
      <li><a href="/stocksmarketsindia/">
        <h2>Markets HOME INDIAN INDICES STOCK ACTION All Stats Top Gainers</h2>
      </a></li>
    </ul>
    """
    articles = MoneyControlService._parse_articles(html, 20)
    assert len(articles) == 1
    assert articles[0]["title"] == "Infosys profit rises as growth improves"


def test_portfolio_cash_and_pnl_are_consistent():
    portfolio = PortfolioManager(initial_cash=100000)
    portfolio.add_position("INFY.NS", 10, 1175)
    portfolio.update_price("INFY.NS", 1200)

    summary = portfolio.summary()

    assert summary["available_cash"] == 88250
    assert summary["total_value"] == 100250
    assert summary["total_pnl"] == 250
    assert summary["positions"][0]["entry"] == 1175
    assert summary["positions"][0]["current"] == 1200
