from backend.services.yahoo_service import YahooService
from backend.algo.bollinger_strategy import BollingerStrategy

stock = YahooService.get_stock("RELIANCE.NS")

result = BollingerStrategy.analyze(stock["df"])

print(result)