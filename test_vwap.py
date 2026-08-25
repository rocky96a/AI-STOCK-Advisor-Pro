from backend.services.yahoo_service import YahooService
from backend.algo.vwap_strategy import VWAPStrategy

stock = YahooService.get_stock("RELIANCE.NS")

result = VWAPStrategy.analyze(stock["df"])

print(result)