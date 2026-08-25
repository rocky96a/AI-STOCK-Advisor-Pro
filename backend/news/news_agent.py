from backend.news.news_fetcher import NewsFetcher
from backend.news.sentiment_engine import (
    SentimentEngine,
)


class NewsAgent:

    @staticmethod
    def analyze(
        symbol,
        company_name=None,
    ):

        news = NewsFetcher.fetch(
            symbol=symbol,
            company_name=company_name,
            limit=20,
        )

        sentiment = SentimentEngine.analyze(
            news
        )

        return {
            "news": news,
            "sentiment": sentiment,
        }