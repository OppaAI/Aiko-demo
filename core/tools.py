"""
core/tools.py
Aiko's tool belt — web search + page fetch via DuckDuckGo.
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


def web_fetch(url: str, max_chars: int = 6000) -> str:
    try:
        resp = httpx.get(
            url,
            timeout=10,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        if resp.status_code != 200:
            return f"[fetch failed: HTTP {resp.status_code}]"
        text = re.sub(r'<[^>]+>', ' ', resp.text)
        text = re.sub(r'\s+', ' ', text).strip()
        # too little content = JS-rendered page, skip it
        if len(text) < 200:
            return "[fetch failed: page appears JS-rendered]"
        return text[:max_chars]
    except Exception as e:
        return f"[fetch failed: {e}]"


def web_search_and_fetch(query: str, max_results: int = 5) -> str:
    """
    Search + fetch top non-blocked result.
    Returns combined string ready for <search_results> injection.
    """
    results = web_search(query, max_results=max_results)

    # extract up to 3 URLs from results
    urls = []
    for line in results.split("\n"):
        line = line.strip()
        if line.startswith("http"):
            urls.append(line)
        if len(urls) >= 3:
            break

    # try each URL until one returns real content
    for url in urls:
        fetched = web_fetch(url)
        if not fetched.startswith("[fetch"):
            results = f"{results}\n\n[Fetched content from: {url}]\n{fetched}"
            break

    return results