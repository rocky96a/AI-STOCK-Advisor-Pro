from backend.services.yahoo_service import YahooService
from backend.algo.supertrend_strategy import SuperTrendStrategy

stock = YahooService.get_stock("RELIANCE.NS")

result = SuperTrendStrategy.analyze(stock["df"])

print(result)