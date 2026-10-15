
import json
from openai import OpenAI
from ddgs import DDGS

# ==================================================
# Configuration
# ==================================================

base_url="https://openrouter.ai/api/v1"
api_key="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"
OPENROUTER_API_KEY = api_key

MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
)

# ==================================================
# DuckDuckGo Search
# ==================================================

def search_web(queries, max_results=6):
    results = []
    seen_urls = set()

    with DDGS() as ddgs:
        for query in queries:
            try:
                for item in ddgs.text(
                    query,
                    max_results=max_results,
                ):
                    url = item.get("href", "")

                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        results.append({
                            "title": item.get("title", ""),
                            "url": url,
                            "snippet": item.get("body", ""),
                        })

            except Exception as exc:
                print(f"Search error: {exc}")

    return results


# ==================================================
# Song Genre Research
# ==================================================

def find_song_genres():
    queries = [
        '"Dariush" Shame Mahtab music metadata',
    ]

    results = search_web(queries)

    if not results:
        raise RuntimeError("No search results found.")

    search_context = json.dumps(
        results,
        ensure_ascii=False,
        indent=2,
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": """
You are a music metadata researcher.

Identify the top 3 most likely genres of the specific
song "SHame Mahtab"  by Dariush

Prioritize song-specific evidence over artist-level labels.
Do not invent genres or sources.
Distinguish verified metadata from inferred genres.
Cite source URLs from the supplied search results.

Return JSON:
{
  "song": "Didi",
  "artist": "Morteza Pashaei",
  "genres": [
    {
      "rank": 1,
      "genre": "...",
      "evidence": "...",
      "confidence": "high/medium/low",
      "sources": ["https://..."]
    }
  ]
}
""",
            },
            {
                "role": "user",
                "content": (
                    "Analyze these search results:\n"
                    + search_context
                ),
            },
        ],
        extra_body={
            "reasoning": {"enabled": True}
        },
    )

    answer = response.choices[0].message.content

    print("\n===== SEARCH SOURCES =====")
    for result in results:
        print(f"\n{result['title']}")
        print(result["url"])
        print(result["snippet"])

    print("\n===== GENRE ANALYSIS =====")
    print(answer)

    return answer


if __name__ == "__main__":
    find_song_genres()

