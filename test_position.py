from backend.services.yahoo_service import YahooService
from backend.algo.position_strategy import PositionStrategy

stock = YahooService.get_stock(
    "RELIANCE.NS",
    interval="1d",
    period="5y"
)

result = PositionStrategy.analyze(stock["df"])

print(result)