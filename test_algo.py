from backend.services.yahoo_service import YahooService
from backend.algo.ema_strategy import EMAStrategy

stock = YahooService.get_stock("RELIANCE.NS")

result = EMAStrategy.analyze(stock["df"])

print(result)