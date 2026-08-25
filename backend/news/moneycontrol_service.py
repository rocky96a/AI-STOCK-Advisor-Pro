import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


class MoneyControlService:

    BASE_URL = "https://www.moneycontrol.com"

    COMPANY_URLS = {
        "INFY": (
            "https://www.moneycontrol.com/"
            "india/stockpricequote/"
            "computers-software/infosys/IT"
        ),
    }

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    BLOCKED_PHRASES = (
        "hello, login",
        "log-in or sign-up",
        "my account",
        "my profile",
        "my portfolio",
        "my watchlist",
        "price alerts",
        "loans up to",
        "credit cards",
        "markets home",
        "stock action",
        "technical trends",
        "economic calendar",
        "mutual funds explore",
        "follow us on",
        "download app",
    )

    STOP_WORDS = {
        "limited",
        "ltd",
        "company",
        "corp",
        "corporation",
        "inc",
        "plc",
        "services",
        "group",
        "industries",
        "india",
    }

    @classmethod
    def _clean_text(cls, text):
        return re.sub(
            r"\s+",
            " ",
            text or "",
        ).strip()

    @classmethod
    def _clean_symbol(cls, symbol):
        if not symbol:
            return ""

        return (
            symbol.upper()
            .replace(".NS", "")
            .replace(".BO", "")
            .strip()
        )

    @classmethod
    def _company_url(
        cls,
        symbol=None,
        company_name=None,
    ):
        """
        Return a Moneycontrol company page.

        Known symbols use an exact company URL.
        """

        clean_symbol = cls._clean_symbol(symbol)

        if clean_symbol in cls.COMPANY_URLS:
            return cls.COMPANY_URLS[clean_symbol]

        return None

    @classmethod
    def _is_valid_article(cls, title, link):
        title_lower = title.lower()

        if len(title) < 25:
            return False

        if any(
            phrase in title_lower
            for phrase in cls.BLOCKED_PHRASES
        ):
            return False

        if not link:
            return False

        if "moneycontrol.com/news/" not in link:
            return False

        return True

    @classmethod
    def _build_search_terms(
        cls,
        symbol=None,
        company_name=None,
    ):
        terms = []

        if symbol:

            clean_symbol = cls._clean_symbol(symbol)

            if clean_symbol:
                terms.append(
                    clean_symbol.lower()
                )

        if company_name:

            company = (
                company_name
                .lower()
                .strip()
            )

            if company:
                terms.append(company)

                words = re.findall(
                    r"[a-zA-Z]{4,}",
                    company,
                )

                for word in words:

                    if word not in cls.STOP_WORDS:
                        terms.append(word)

        return list(
            dict.fromkeys(terms)
        )

    @classmethod
    def _article_matches_stock(
        cls,
        title,
        summary,
        symbol=None,
        company_name=None,
    ):
        """
        The article came from the company's
        Moneycontrol page, so matching is already
        strongly implied.

        We still perform a lightweight validation
        to prevent unrelated articles from entering
        the news feed.
        """

        text = (
            f"{title} {summary}"
        ).lower()

        terms = cls._build_search_terms(
            symbol=symbol,
            company_name=company_name,
        )

        if not terms:
            return True

        for term in terms:

            if not term:
                continue

            pattern = (
                r"\b"
                + re.escape(term)
                + r"\b"
            )

            if re.search(
                pattern,
                text,
            ):
                return True

        return False

    @classmethod
    def _extract_articles(
        cls,
        soup,
        symbol=None,
        company_name=None,
        limit=20,
    ):
        """
        Extract genuine Moneycontrol news articles
        from the company-specific page.
        """

        matched_articles = []
        seen = set()

        for tag in soup.find_all(
            "a",
            href=True,
        ):

            title = cls._clean_text(
                tag.get_text(
                    " ",
                    strip=True,
                )
            )

            link = urljoin(
                cls.BASE_URL,
                tag.get("href", ""),
            )

            if not cls._is_valid_article(
                title,
                link,
            ):
                continue

            # -----------------------------------------
            # Duplicate protection
            # -----------------------------------------

            key = link.split("?")[0]

            if key in seen:
                continue

            seen.add(key)

            # -----------------------------------------
            # Find surrounding article container
            # -----------------------------------------

            container = (
                tag.find_parent("article")
                or tag.find_parent("li")
                or tag.parent
            )

            summary = ""

            if container:

                paragraph = container.find("p")

                if paragraph:

                    summary = cls._clean_text(
                        paragraph.get_text(
                            " ",
                            strip=True,
                        )
                    )

            if not summary:
                summary = title

            # -----------------------------------------
            # Stock validation
            # -----------------------------------------

            if not cls._article_matches_stock(
                title=title,
                summary=summary,
                symbol=symbol,
                company_name=company_name,
            ):
                continue

            matched_articles.append({
                "title": title,
                "summary": summary[:500],
                "url": link,
                "publisher": "Moneycontrol",
            })

            if len(matched_articles) >= limit:
                break

        return matched_articles

    @classmethod
    def get_latest_news(
        cls,
        symbol=None,
        company_name=None,
        limit=20,
    ):

        try:

            url = cls._company_url(
                symbol=symbol,
                company_name=company_name,
            )

            if not url:

                print(
                    "[MoneyControl] "
                    f"No company URL for {symbol}"
                )

                return []

            print(
                "[MoneyControl] COMPANY PAGE:",
                url,
            )

            response = requests.get(
                url,
                headers=cls.HEADERS,
                timeout=15,
            )

            response.raise_for_status()

            soup = BeautifulSoup(
                response.text,
                "lxml",
            )

            articles = cls._extract_articles(
                soup=soup,
                symbol=symbol,
                company_name=company_name,
                limit=limit,
            )

            print(
                "[MoneyControl] ARTICLES:",
                len(articles),
            )

            return articles

        except Exception as e:

            print(
                "[MoneyControl] ERROR:",
                e,
            )

            return []