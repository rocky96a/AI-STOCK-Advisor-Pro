from backend.services.yahoo_service import YahooService
from backend.algo.orb_strategy import ORBStrategy

stock = YahooService.get_stock(
    "RELIANCE.NS",
    interval="5m",
    period="5d"
)

result = ORBStrategy.analyze(stock["df"])

print(result)