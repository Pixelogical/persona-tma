
from pathlib import Path
import requests
from bs4 import BeautifulSoup

url = "https://www.last.fm/music/Morteza+Pashaei/_/Didi"

session = requests.Session()
session.headers["User-Agent"] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/153.0.0.0 Safari/537.36"
)

# Load your existing cookie export.
import json

with open("lastfm_cookies.json", encoding="utf-8") as f:
    cookies = json.load(f)

for c in cookies:
    if c.get("name") and c.get("value") is not None:
        session.cookies.set(
            c["name"],
            c["value"],
            domain=c.get("domain", ".last.fm"),
            path=c.get("path", "/"),
        )

response = session.get(url, timeout=30)
html = response.text

Path("lastfm_response.html").write_text(
    html, encoding="utf-8"
)

soup = BeautifulSoup(html, "html.parser")

print("Status:", response.status_code)
print("Final URL:", response.url)
print("Content-Type:", response.headers.get("Content-Type"))
print("HTML title:", soup.title.get_text(strip=True) if soup.title else None)
print("Related Tags found:", bool(
    soup.select_one("section.catalogue-tags")
))
print("Challenge asset present:", "_fs-ch-" in html)
print("Saved: lastfm_response.html")

