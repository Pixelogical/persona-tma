# time_ir_scraper.py

from __future__ import annotations

import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import Optional


@dataclass
class Quote:
    quote: str
    author: str


class TimeIRScraper:
    BASE_URL = "https://time.ir"

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/154.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
        })

    def get_html(self, url: str) -> str:
        response = self.session.get(
            url,
            timeout=self.timeout,
        )
        response.raise_for_status()
        response.encoding = response.apparent_encoding or response.encoding
        return response.text

    def parse_quote(self, html: str) -> Optional[Quote]:
        soup = BeautifulSoup(html, "html.parser")

        # Find the author link first. This is more stable than
        # depending on generated CSS module class names.
        author_link = soup.find(
            "a",
            href=lambda href: (
                href is not None
                and (
                    "wikipedia.org/wiki/" in href
                    or "wiki/" in href
                )
            ),
        )

        if not author_link:
            return None

        author = author_link.get_text(" ", strip=True)

        # The quote is inside the same parent/root container.
        container = author_link.parent

        # Walk upward until we find a container containing
        # both the author and a reasonable text element.
        for _ in range(5):
            if container is None:
                break

            quote_element = container.select_one(
                "div[class*='ExpandableText'] div"
            )

            if quote_element:
                quote = quote_element.get_text(" ", strip=True)

                if quote and quote != author:
                    return Quote(
                        quote=quote,
                        author=author,
                    )

            container = container.parent

        return None

    def scrape(self, url: str) -> Optional[Quote]:
        html = self.get_html(url)
        return self.parse_quote(html)


def scrape_quote(url: str) -> Optional[dict]:
    """
    Convenience function.

    Returns:
        {
            "quote": "...",
            "author": "..."
        }

        or None if no quote was found.
    """
    scraper = TimeIRScraper()
    result = scraper.scrape(url)

    if result is None:
        return None

    return {
        "quote": result.quote,
        "author": result.author,
    }


if __name__ == "__main__":
    url = "https://time.ir/"

    result = scrape_quote(url)

    if result:
        print(result)
    else:
        print("Quote not found.")