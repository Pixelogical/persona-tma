import os
from google import genai
from google.genai import types

client = genai.Client(
    api_key="AQ.Ab8RN6JKsmAryalo3-LIWU-xaSjeRLCGFykrjf5DoqGTvg3xiQ"
)

prompt = """
Search the internet for the Persian song "Didi"
by Morteza Pashaei (مرتضی پاشایی).

Identify the top 3 most likely music genres for this
specific song, ranked from most likely to least likely.

Use evidence from reliable music databases, artist/song
metadata, and relevant web pages.

Do not confuse the song with other songs by the same artist.
Distinguish confirmed metadata from your own inference.

Return:
1. Genre
2. Evidence and source URL
3. Confidence (high, medium, or low)

If reliable evidence is insufficient, say so rather
than inventing genres.
"""

response = client.models.generate_content(
    model="gemini-3.5-flash-lite",
    contents=prompt,
    config=types.GenerateContentConfig(
        tools=[
            types.Tool(
                google_search=types.GoogleSearch()
            )
        ],
        temperature=0.1,
    ),
)

print(response.text)

# Print grounding sources when available
metadata = response.candidates[0].grounding_metadata

if metadata and metadata.grounding_chunks:
    print("\nSources:")
    for chunk in metadata.grounding_chunks:
        if chunk.web:
            print(f"- {chunk.web.title}: {chunk.web.uri}")



