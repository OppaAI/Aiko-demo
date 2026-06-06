"""
core/tools.py

Aiko's tool belt — starting with web search via DuckDuckGo.
All tools are plain functions that return strings ready for context injection.
"""

import os
from duckduckgo_search import DDGS

def web_search(query: str, max_results: int = 3) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
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