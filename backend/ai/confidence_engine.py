class ConfidenceEngine:

    @staticmethod
    def calculate(technical, ml, algorithmic, news):

        score = 0.0
        reasons = []

        # ==================================================
        # Technical Analysis
        # ==================================================

        tech_signal = technical.get("signal", "HOLD")
        tech_conf = float(
            technical.get("confidence", 0)
        )
        tech_strength = technical.get(
            "strength",
            "WEAK",
        )

        if tech_signal in ("BUY", "STRONG BUY"):

            score += tech_conf * 0.30

            reasons.append(
                "Technical Trend Bullish"
            )

        elif tech_signal in ("SELL", "STRONG SELL"):

            score -= tech_conf * 0.30

            reasons.append(
                "Technical Trend Bearish"
            )

        # ==================================================
        # Machine Learning
        # ==================================================

        if ml and ml.get("available", False):

            ml_conf = float(
                ml.get("confidence", 0)
            )

            ml_direction = ml.get(
                "direction"
            )

            if ml_direction == "UP":

                score += ml_conf * 0.30

                reasons.append(
                    "ML predicts upside"
                )

            elif ml_direction == "DOWN":

                score -= ml_conf * 0.30

                reasons.append(
                    "ML predicts downside"
                )

        # ==================================================
        # News Sentiment
        # ==================================================

        #
        # IMPORTANT:
        #
        # No relevant articles != Neutral news.
        #
        # If there are zero relevant articles, news contributes
        # NOTHING to the confidence score.
        #

        news_articles = 0

        if news:

            news_articles = int(
                news.get("articles", 0)
            )

            sentiment = news.get(
                "sentiment",
                "Neutral",
            )

            news_conf = float(
                news.get("confidence", 0)
            )

            if news_articles > 0:

                if sentiment == "Bullish":

                    score += (
                        news_conf * 0.20
                    )

                    reasons.append(
                        "Positive News Sentiment"
                    )

                elif sentiment == "Bearish":

                    score -= (
                        news_conf * 0.20
                    )

                    reasons.append(
                        "Negative News Sentiment"
                    )

                else:

                    reasons.append(
                        "Neutral News Sentiment"
                    )

            else:

                reasons.append(
                    "No relevant news available"
                )

        else:

            reasons.append(
                "No relevant news available"
            )

        # ==================================================
        # Algorithmic Strategies
        # ==================================================

        algo_signal = algorithmic.get(
            "signal",
            "HOLD",
        )

        algo_conf = float(
            algorithmic.get(
                "confidence",
                0,
            )
        )

        if algo_signal == "BUY":

            score += (
                algo_conf * 0.20
            )

            reasons.append(
                "Algorithmic strategies bullish"
            )

        elif algo_signal == "SELL":

            score -= (
                algo_conf * 0.20
            )

            reasons.append(
                "Algorithmic strategies bearish"
            )

        # ==================================================
        # Weak Technical Trend Protection
        # ==================================================

        if tech_strength == "WEAK":

            if score > 0:

                score = min(
                    score,
                    24.0,
                )

            elif score < 0:

                score = max(
                    score,
                    -24.0,
                )

            reasons.append(
                "Technical trend strength is weak"
            )

        # ==================================================
        # Confidence
        # ==================================================

        confidence = max(
            0.0,
            min(
                abs(score),
                100.0,
            ),
        )

        # ==================================================
        # Grade
        # ==================================================

        if confidence >= 90:

            grade = "A+"

        elif confidence >= 80:

            grade = "A"

        elif confidence >= 70:

            grade = "B"

        elif confidence >= 60:

            grade = "C"

        else:

            grade = "D"

        # ==================================================
        # Recommendation
        # ==================================================

        if score >= 25:

            recommendation = "STRONG BUY"

        elif score >= 5:

            recommendation = "BUY"

        elif score <= -25:

            recommendation = "STRONG SELL"

        elif score <= -5:

            recommendation = "SELL"

        else:

            recommendation = "HOLD"

        # ==================================================
        # Return
        # ==================================================

        return {
            "confidence": round(
                confidence,
                2,
            ),

            "grade": grade,

            "recommendation": recommendation,

            "score": round(
                score,
                2,
            ),

            "reasons": reasons,
        }
