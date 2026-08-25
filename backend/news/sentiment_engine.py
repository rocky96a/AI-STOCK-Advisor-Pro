from backend.news.finbert_model import FinBERT


class SentimentEngine:

    @staticmethod
    def analyze(news):

        if not news:
            return {
                "sentiment": "Neutral",
                "score": 0.0,
                "confidence": 0.0,
                "articles": 0,
                "bullish": 0,
                "bearish": 0,
                "neutral": 0,
                "details": [],
            }

        classifier = FinBERT.load()

        bullish = 0
        bearish = 0
        neutral = 0

        confidence_sum = 0.0
        details = []

        valid_articles = 0

        for article in news:

            title = (
                article.get("title") or ""
            ).strip()

            summary = (
                article.get("summary") or ""
            ).strip()

            text = f"{title}. {summary}".strip()

            if len(title) < 15:
                continue

            if len(text) < 20:
                continue

            try:
                result = classifier(
                    text[:512]
                )[0]

                label = (
                    result["label"]
                    .lower()
                    .strip()
                )

                score = float(
                    result["score"]
                )

            except Exception as e:

                print(
                    f"Sentiment error: {e}"
                )

                continue

            valid_articles += 1
            confidence_sum += score

            if label == "positive":

                bullish += 1
                article_sentiment = "Bullish"

            elif label == "negative":

                bearish += 1
                article_sentiment = "Bearish"

            else:

                neutral += 1
                article_sentiment = "Neutral"

            details.append({
                "title": title,
                "sentiment": article_sentiment,
                "confidence": round(
                    score * 100,
                    2,
                ),
            })

        if valid_articles == 0:
            return {
                "sentiment": "Neutral",
                "score": 0.0,
                "confidence": 0.0,
                "articles": 0,
                "bullish": 0,
                "bearish": 0,
                "neutral": 0,
                "details": [],
            }

        # Require a clear majority.
        if bullish > bearish and bullish > neutral:
            final = "Bullish"

        elif bearish > bullish and bearish > neutral:
            final = "Bearish"

        else:
            final = "Neutral"

        confidence = (
            confidence_sum
            / valid_articles
        )

        # Neutral news should not create bullish/bearish
        # confidence.
        if final == "Neutral":
            directional_score = 0.0
        else:
            directional_score = (
                (bullish - bearish)
                / valid_articles
            )

        return {
            "sentiment": final,

            "score": round(
                directional_score,
                4,
            ),

            "confidence": round(
                confidence * 100,
                2,
            ),

            "articles": valid_articles,

            "bullish": bullish,
            "bearish": bearish,
            "neutral": neutral,

            "details": details,
        }