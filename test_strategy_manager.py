from backend.services.yahoo_service import YahooService
from backend.algo.strategy_manager import StrategyManager

stock = YahooService.get_stock(

    "RELIANCE.NS",

    interval="1d",

    period="3y"

)

result = StrategyManager.analyze(stock["df"])

print(result)