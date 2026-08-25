from backend.services.yahoo_service import YahooService
from backend.algo.breakout_strategy import BreakoutStrategy

stock = YahooService.get_stock("RELIANCE.NS")

result = BreakoutStrategy.analyze(stock["df"])

print(result)