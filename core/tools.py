"""
core/tools.py

Aiko's tool belt — starting with web search via DuckDuckGo.
All tools are plain functions that return strings ready for context injection.
"""

import re
import httpx
from ddgs import DDGS

def web_search(query: str, max_results: int = 5) -> str:
    try:
        results = DDGS().text(query, max_results=max_results)
    except Exception as e:
        return f"[search failed: {e}]"

    if not results:
        return f"[no results found for: {query}]"

    lines = [f"[Web search results for: {query}]"]
    for i, r in enumerate(results, 1):
        title   = r.get("title", "").strip()
        url     = r.get("href", "").strip()
        content = r.get("body", "").strip()
        lines.append(f"{i}. {title}\n   {url}\n   {content}")
    return "\n\n".join(lines)
    
def web_fetch(url: str, max_chars: int = 3000) -> str:
    try:
        import httpx
        resp = httpx.get(url, timeout=10, follow_redirects=True,
                        headers={"User-Agent": "Mozilla/5.0"})
        # strip html tags
        import re
        text = re.sub(r'<[^>]+>', ' ', resp.text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:max_chars]
    except Exception as e:
        return f"[fetch failed: {e}]"
        