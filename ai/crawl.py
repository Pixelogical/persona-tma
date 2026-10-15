
import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://www.last.fm/music/Morteza+Pashaei/_/Didi"
COOKIE_FILE = Path("lastfm_cookies.json")


def load_cookies(session):
    with COOKIE_FILE.open("r", encoding="utf-8") as f:
        cookies = json.load(f)

    # Cookie-Editor usually exports a list of cookie objects.
    if not isinstance(cookies, list):
        raise ValueError(
            "Expected a JSON list of cookies. "
            "Check the export format."
        )

    for cookie in cookies:
        name = cookie.get("name")
        value = cookie.get("value")
        domain = cookie.get("domain", ".last.fm")
        path = cookie.get("path", "/")

        if name and value is not None:
            session.cookies.set(
                name,
                value,
                domain=domain,
                path=path,
            )


def get_related_tags(html):
    soup = BeautifulSoup(html, "html.parser")

    section = soup.select_one("section.catalogue-tags")
    if section is None:
        return None

    return [
        a.get_text(strip=True)
        for a in section.select("ul.tags-list--global li.tag a")
    ]


def main():
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/153.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    })

    load_cookies(session)

    response = session.get(URL, timeout=20)

    print("HTTP status:", response.status_code)
    print("Final URL:", response.url)

    response.raise_for_status()

    tags = get_related_tags(response.text)

    if tags is None:
        print("Related Tags section not found.")
        print("Response preview:", response.text[:500])
        print(
            "The page may have returned an error, "
            "a different layout, or a challenge page."
        )
        return

    print("Related tags:", tags)


if __name__ == "__main__":
    main()

