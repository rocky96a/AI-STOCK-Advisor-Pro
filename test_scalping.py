from backend.services.yahoo_service import YahooService
from backend.algo.scalping_strategy import ScalpingStrategy


stock = YahooService.get_stock(
    "RELIANCE.NS",
    interval="5m",
    period="5d"
)

if stock is None:

    print("Could not load stock data")

else:

    result = ScalpingStrategy.analyze(
        stock["df"],
        interval="5m"
    )

    print(result)