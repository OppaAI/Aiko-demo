"""
core/tools.py
Aiko's tool belt — web search + page fetch via DuckDuckGo.
All tools are plain functions that return strings ready for context injection.
"""
import re
import httpx
from ddgs import DDGS

# domains that reliably block scrapers — skip fetching these
_FETCH_BLOCKLIST = {
    "investing.com", "bloomberg.com", "wsj.com", "ft.com",
    "reuters.com", "nytimes.com", "washingtonpost.com",
}


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
    from urllib.parse import urlparse
    domain = urlparse(url).netloc.replace("www.", "")
    if any(blocked in domain for blocked in _FETCH_BLOCKLIST):
        return f"[fetch skipped: {domain} blocks scrapers]"
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
        return text[:max_chars]
    except Exception as e:
        return f"[fetch failed: {e}]"


def web_search_and_fetch(query: str, max_results: int = 5) -> str:
    """
    Search + fetch top non-blocked result.
    Returns combined string ready for <search_results> injection.
    """
    results = web_search(query, max_results=max_results)

    # extract URLs from results, try up to 3
    urls = []
    for line in results.split("\n"):
        line = line.strip()
        if line.startswith("http"):
            urls.append(line)
        if len(urls) >= 3:
            break

    for url in urls:
        fetched = web_fetch(url)
        if not fetched.startswith("[fetch"):
            results = f"{results}\n\n[Fetched content from: {url}]\n{fetched}"
            break

    return results
    