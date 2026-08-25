import re
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote

from backend.news.moneycontrol_service import MoneyControlService


class NewsFetcher:
    """Fetch stock news with Moneycontrol + Google News RSS fallback."""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
        ),
        "Accept-Language": "en-IN,en;q=0.9",
    }

    @staticmethod
    def _clean_symbol(symbol):
        return (symbol or "").upper().strip()

    @classmethod
    def _google_news(cls, symbol, company_name=None, limit=20):
        symbol = cls._clean_symbol(symbol)
        clean = re.sub(r"\.(NS|BO)$", "", symbol, flags=re.I)

        terms = []
        if company_name:
            terms.append(f'"{company_name.strip()}"')
        if clean:
            terms.append(f'"{clean}"')
        if symbol:
            terms.append(f'"{symbol}"')

        if not terms:
            return []

        query = " OR ".join(terms)
        url = (
            "https://news.google.com/rss/search?q="
            + quote(query)
            + "&hl=en-IN&gl=IN&ceid=IN:en"
        )

        try:
            response = requests.get(
                url,
                headers=cls.HEADERS,
                timeout=12,
            )
            response.raise_for_status()
            root = ET.fromstring(response.content)
        except Exception as exc:
            print("[GoogleNews] ERROR:", exc)
            return []

        articles = []
        seen = set()

        for item in root.findall("./channel/item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            description = (item.findtext("description") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            source_node = item.find("source")
            publisher = (
                (source_node.text or "").strip()
                if source_node is not None
                else "Google News"
            )

            if not title or not link:
                continue

            key = link.split("?")[0]
            if key in seen:
                continue
            seen.add(key)

            summary = re.sub(r"<[^>]+>", " ", description)
            summary = re.sub(r"\s+", " ", summary).strip()

            articles.append({
                "title": title,
                "summary": summary[:500],
                "url": link,
                "publisher": publisher or "Google News",
                "published": pub_date,
            })

            if len(articles) >= limit:
                break

        print(f"[GoogleNews] {symbol}: {len(articles)} articles")
        return articles

    @classmethod
    def fetch(cls, symbol, company_name=None, limit=20):
        try:
            articles = MoneyControlService.get_latest_news(
                symbol=symbol,
                company_name=company_name,
                limit=limit,
            )
            if articles:
                return articles
        except Exception as exc:
            print("[NewsFetcher] Moneycontrol fallback:", exc)

        return cls._google_news(
            symbol=symbol,
            company_name=company_name,
            limit=limit,
        )
