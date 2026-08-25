from backend.services.yahoo_service import YahooService
from backend.algo.swing_strategy import SwingStrategy

stock = YahooService.get_stock(
    "RELIANCE.NS",
    interval="1d",
    period="2y"
)

result = SwingStrategy.analyze(stock["df"])

print(result)