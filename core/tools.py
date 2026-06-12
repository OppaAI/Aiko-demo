"""
core/tools.py
Aiko's tool belt — web search, weather, timezone, currency, jokes, anime info.

All tools return plain strings ready for context injection into the system prompt.
No API keys required — all free/no-auth endpoints.

Tools:
  web_search(query)            — SearXNG JSON API
  web_fetch(url)               — raw page fetch + HTML strip
  web_search_and_fetch(query)  — search + fetch top result, combined string
  get_weather(location)        — wttr.in (no key)
  get_timezone(location)       — worldtimeapi.org (no key)
  get_currency(amount, fr, to) — Frankfurter API (no key, ECB data)
  get_joke()                   — JokeAPI (no key)
  get_anime(query)             — Jikan API / MyAnimeList (no key)

Intent detection (used by think.py as fallback when LLM tool-calling
doesn't produce a tool_call):
  is_weather_intent(text)
  is_timezone_intent(text)
  is_currency_intent(text)
  is_joke_intent(text)
  is_anime_intent(text)
  is_search_intent(text)

LLM-driven tool calling (preferred path, used by think.py):
  TOOL_SCHEMAS   — OpenAI function-calling spec for all tools
  TOOL_DISPATCH  — maps tool name -> (context_tag, callable)

Environment variables:
  SEARXNG_BASE_URL — your SearXNG HF Space URL, e.g. https://oppaai-searxng.hf.space
"""

import os
import re
import time
import httpx

# ── config ────────────────────────────────────────────────────────────────────

SEARXNG_BASE_URL = os.getenv("SEARXNG_BASE_URL", "")

# ── intent patterns ───────────────────────────────────────────────────────────

_SEARCH_TRIGGERS = re.compile(
    r"\b(check (?:the )?internet|search (?:the )?web|look it up|go online|"
    r"search online|check online|look online|google that|browse for|"
    r"fetch.*web|web search|internet search)\b",
    re.IGNORECASE,
)

_WEATHER_TRIGGERS = re.compile(
    r"\b(weather|forecast|temperature|how hot|how cold|rain|sunny|"
    r"humidity|wind|climate today|will it rain|umbrella)\b",
    re.IGNORECASE,
)

_TIMEZONE_TRIGGERS = re.compile(
    r"\b(what time|current time|time in|time at|timezone|time zone|"
    r"what's the time|local time)\b",
    re.IGNORECASE,
)

_CURRENCY_TRIGGERS = re.compile(
    r"\b(convert|exchange rate|how much is|currency|"
    r"usd|eur|jpy|gbp|krw|cad|aud|sgd|thb)"
    r".*\b(to|in|into)\b"
    r"|\b(to|in|into)\b.*"
    r"\b(usd|eur|jpy|gbp|krw|cad|aud|sgd|thb)\b",
    re.IGNORECASE,
)

_JOKE_TRIGGERS = re.compile(
    r"\b(tell me a joke|joke|make me laugh|something funny|"
    r"funny joke|random joke|cheer me up)\b",
    re.IGNORECASE,
)

_ANIME_TRIGGERS = re.compile(
    r"\b(anime|manga|light novel|visual novel|tell me about|"
    r"search anime|find anime|what is|who is)"
    r".*\b(anime|manga|otaku|isekai|shounen|shoujo|seinen)\b"
    r"|\b(anime|manga)\b",
    re.IGNORECASE,
)


def is_search_intent(text: str)   -> bool: return bool(_SEARCH_TRIGGERS.search(text))
def is_weather_intent(text: str)  -> bool: return bool(_WEATHER_TRIGGERS.search(text))
def is_timezone_intent(text: str) -> bool: return bool(_TIMEZONE_TRIGGERS.search(text))
def is_currency_intent(text: str) -> bool: return bool(_CURRENCY_TRIGGERS.search(text))
def is_joke_intent(text: str)     -> bool: return bool(_JOKE_TRIGGERS.search(text))
def is_anime_intent(text: str)    -> bool: return bool(_ANIME_TRIGGERS.search(text))


# ── query cleaners ────────────────────────────────────────────────────────────

_LEADING_JUNK = re.compile(r"^[\s,;.\-—–]+")
_LEADING_FILLER = re.compile(
    r"^(and\s+|but\s+|then\s+|so\s+|for\s+"
    r"|hey aiko[,.]?\s*|aiko[,.]?\s*"
    r"|can you\s*|could you\s*|please\s*"
    r"|tell me\s*|give me\s*|show me\s*|get me\s*"
    r"|find\s+(?:out\s+)?|look\s+(?:up\s+)?"
    r"|(?:some\s+)?(?:detailed?\s+)?info(?:rmation)?\s+(?:about\s+|on\s+)?"
    r"|(?:more\s+)?details?\s+(?:about\s+|on\s+)?"
    r"|about\s+)",
    re.IGNORECASE,
)


def _strip_filler(text: str) -> str:
    cleaned = text.strip()
    prev = None
    while prev != cleaned:
        prev    = cleaned
        cleaned = _LEADING_JUNK.sub("", cleaned).strip()
        cleaned = _LEADING_FILLER.sub("", cleaned).strip()
    return cleaned or text.strip()


def extract_search_query(text: str) -> str:
    return _strip_filler(_SEARCH_TRIGGERS.sub("", text))


def extract_location(text: str) -> str:
    """Pull location from weather/timezone queries."""
    # strip common question prefixes
    cleaned = re.sub(
        r"^(what(?:'s| is) the (?:weather|temperature|forecast|time)|"
        r"how(?:'s| is) the weather|weather|forecast|time|timezone)\s*",
        "", text, flags=re.IGNORECASE,
    ).strip()
    cleaned = re.sub(r"^(in|at|for|of)\s+", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"\?$", "", cleaned).strip()
    return cleaned or "Tokyo"


def extract_currency_parts(text: str) -> tuple[float, str, str]:
    """
    Parse amount + from/to currencies from natural language.
    Returns (amount, from_currency, to_currency).
    Defaults: 1, USD, JPY.
    """
    amount_match = re.search(r"(\d+(?:\.\d+)?)", text)
    amount = float(amount_match.group(1)) if amount_match else 1.0

    currencies = re.findall(
        r"\b(USD|EUR|JPY|GBP|KRW|CAD|AUD|SGD|THB)\b", text, re.IGNORECASE
    )
    currencies = [c.upper() for c in currencies]

    from_cur = currencies[0] if len(currencies) > 0 else "USD"
    to_cur   = currencies[1] if len(currencies) > 1 else "JPY"
    return amount, from_cur, to_cur


def extract_anime_query(text: str) -> str:
    cleaned = re.sub(
        r"\b(tell me about|search|find|what is|who is|anime called|"
        r"manga called|recommend|info on|information about)\b",
        "", text, flags=re.IGNORECASE,
    ).strip()
    cleaned = re.sub(r"\b(anime|manga)\b", "", cleaned, flags=re.IGNORECASE).strip()
    return _strip_filler(cleaned) or text.strip()


# ── web search ────────────────────────────────────────────────────────────────

def web_search(query: str, max_results: int = 5) -> str:
    """Search via SearXNG JSON API. Falls back to error string on failure."""
    if not SEARXNG_BASE_URL:
        return "[search unavailable: SEARXNG_BASE_URL not set]"
    # strip stray quotes and whitespace
    query = query.strip().strip("'\"")
    try:        resp = httpx.get(
            f"{SEARXNG_BASE_URL.rstrip('/')}/search",
            params={"q": query, "format": "json", "count": max_results},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if not results:
            return f"[no results found for: {query}]"
        lines = [f"[Web search results for: {query}]"]
        for i, r in enumerate(results[:max_results], 1):
            lines.append(
                f"{i}. {r.get('title', '').strip()}\n"
                f"   {r.get('url', '').strip()}\n"
                f"   {r.get('content', '').strip()}"
            )
        return "\n\n".join(lines)
    except Exception as e:
        return f"[search failed: {e}]"


def web_fetch(url: str, max_chars: int = 6000) -> str:
    """Fetch a URL and strip HTML tags. Returns plain text."""
    try:
        resp = httpx.get(
            url,
            timeout=10,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        if resp.status_code != 200:
            return f"[fetch failed: HTTP {resp.status_code}]"
        text = re.sub(r"<[^>]+>", " ", resp.text)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) < 200:
            return "[fetch failed: page appears JS-rendered]"
        return text[:max_chars]
    except Exception as e:
        return f"[fetch failed: {e}]"


def web_search_and_fetch(query: str, max_results: int = 5) -> str:
    """Search + fetch top result. Returns combined string for context injection."""
    query = query.strip().strip("'\"")
    results = web_search(query, max_results=max_results)
    urls    = re.findall(r"https?://[^\s]+", results)[:3]
    for url in urls:
        fetched = web_fetch(url)
        if not fetched.startswith("[fetch"):
            return f"{results}\n\n[Fetched content from: {url}]\n{fetched}"
    return results


# ── weather ───────────────────────────────────────────────────────────────────

def get_weather(location: str) -> str:
    """
    Fetch current weather via wttr.in (no API key needed).
    Returns a concise summary string.
    """
    try:
        resp = httpx.get(
            "https://wttr.in/",
            params={"format": "j1", "q": location},
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        resp.raise_for_status()
        data    = resp.json()
        current = data["current_condition"][0]
        area    = data["nearest_area"][0]

        city    = area["areaName"][0]["value"]
        country = area["country"][0]["value"]
        desc    = current["weatherDesc"][0]["value"]
        temp_c  = current["temp_C"]
        temp_f  = current["temp_F"]
        feels_c = current["FeelsLikeC"]
        humidity = current["humidity"]
        wind_kmph = current["windspeedKmph"]

        return (
            f"[Weather for {city}, {country}]\n"
            f"Condition : {desc}\n"
            f"Temp      : {temp_c}°C / {temp_f}°F (feels like {feels_c}°C)\n"
            f"Humidity  : {humidity}%\n"
            f"Wind      : {wind_kmph} km/h"
        )
    except Exception as e:
        return f"[weather fetch failed: {e}]"


# ── timezone ──────────────────────────────────────────────────────────────────

def get_timezone(location: str) -> str:
    """
    Fetch current local time for a location via worldtimeapi.org.
    Falls back to timezone search if direct city lookup fails.
    """
    # worldtimeapi uses timezone strings like "Asia/Tokyo"
    # try to map common city names first
    _CITY_MAP = {
        "tokyo": "Asia/Tokyo", "osaka": "Asia/Tokyo",
        "seoul": "Asia/Seoul", "beijing": "Asia/Shanghai",
        "shanghai": "Asia/Shanghai", "hong kong": "Asia/Hong_Kong",
        "singapore": "Asia/Singapore", "bangkok": "Asia/Bangkok",
        "jakarta": "Asia/Jakarta", "london": "Europe/London",
        "paris": "Europe/Paris", "berlin": "Europe/Berlin",
        "new york": "America/New_York", "los angeles": "America/Los_Angeles",
        "chicago": "America/Chicago", "sydney": "Australia/Sydney",
        "melbourne": "Australia/Melbourne", "dubai": "Asia/Dubai",
        "moscow": "Europe/Moscow", "toronto": "America/Toronto",
    }

    tz = _CITY_MAP.get(location.lower().strip())

    if not tz:
        # try worldtimeapi timezone list search
        try:
            resp = httpx.get("https://worldtimeapi.org/api/timezone", timeout=8)
            all_zones = resp.json()
            loc_lower = location.lower().replace(" ", "_")
            matches   = [z for z in all_zones if loc_lower in z.lower()]
            tz        = matches[0] if matches else None
        except Exception:
            pass

    if not tz:
        return f"[timezone not found for: {location}]"

    try:
        resp = httpx.get(f"https://worldtimeapi.org/api/timezone/{tz}", timeout=8)
        resp.raise_for_status()
        data     = resp.json()
        datetime_str = data.get("datetime", "")[:19].replace("T", " ")
        weekday      = data.get("day_of_week", "")
        days         = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]
        day_name     = days[int(weekday)] if str(weekday).isdigit() else ""
        utc_offset   = data.get("utc_offset", "")

        return (
            f"[Time in {location.title()}]\n"
            f"Local time : {datetime_str} ({day_name})\n"
            f"Timezone   : {tz}\n"
            f"UTC offset : {utc_offset}"
        )
    except Exception as e:
        return f"[timezone fetch failed: {e}]"


# ── currency ──────────────────────────────────────────────────────────────────

def get_currency(amount: float, from_currency: str, to_currency: str) -> str:
    """
    Convert currency via Frankfurter API (ECB data, no key needed).
    Supports: USD, EUR, JPY, GBP, KRW, CAD, AUD, SGD, THB and more.
    """
    try:
        resp = httpx.get(
            "https://api.frankfurter.app/latest",
            params={
                "amount": amount,
                "from":   from_currency.upper(),
                "to":     to_currency.upper(),
            },
            timeout=8,
        )
        resp.raise_for_status()
        data   = resp.json()
        rate   = data["rates"].get(to_currency.upper())
        base   = data["base"]
        date   = data["date"]

        if rate is None:
            return f"[currency: {to_currency} not supported]"

        return (
            f"[Currency conversion — {date}]\n"
            f"{amount:,.2f} {base} = {rate:,.2f} {to_currency.upper()}\n"
            f"Rate: 1 {base} = {rate/amount:.4f} {to_currency.upper()}"
        )
    except Exception as e:
        return f"[currency fetch failed: {e}]"


# ── joke ──────────────────────────────────────────────────────────────────────

def get_joke() -> str:
    """
    Fetch a random safe joke from JokeAPI (no key needed).
    Filters out NSFW, religious, political, racist, sexist content.
    """
    try:
        resp = httpx.get(
            "https://v2.jokeapi.dev/joke/Any",
            params={
                "blacklistFlags": "nsfw,religious,political,racist,sexist,explicit",
                "safe-mode":      True,
                "type":           "twopart",
            },
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("type") == "twopart":
            return f"{data['setup']}\n\n...{data['delivery']}"
        return data.get("joke", "[no joke found]")
    except Exception as e:
        return f"[joke fetch failed: {e}]"


# ── anime ─────────────────────────────────────────────────────────────────────

def get_anime(query: str) -> str:
    """
    Search anime via Jikan API (MyAnimeList, no key needed).
    Returns top 3 results with title, score, synopsis, and genres.
    """
    try:
        resp = httpx.get(
            "https://api.jikan.moe/v4/anime",
            params={"q": query, "limit": 3, "sfw": True},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json().get("data", [])

        if not results:
            return f"[no anime found for: {query}]"

        lines = [f"[Anime search results for: {query}]"]
        for a in results:
            title    = a.get("title", "Unknown")
            score    = a.get("score") or "N/A"
            episodes = a.get("episodes") or "?"
            status   = a.get("status", "")
            synopsis = (a.get("synopsis") or "No synopsis available.")[:300]
            genres   = ", ".join(g["name"] for g in a.get("genres", []))
            url      = a.get("url", "")

            lines.append(
                f"• {title}\n"
                f"  Score: {score} | Episodes: {episodes} | Status: {status}\n"
                f"  Genres: {genres}\n"
                f"  {synopsis}{'...' if len(a.get('synopsis','')) > 300 else ''}\n"
                f"  {url}"
            )
        return "\n\n".join(lines)
    except Exception as e:
        return f"[anime fetch failed: {e}]"


# ── LLM tool-calling schemas + dispatch ─────────────────────────────────────────

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather conditions for a city or location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name, e.g. 'Tokyo' or 'Vancouver, BC'",
                    }
                },
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_timezone",
            "description": "Get the current local time and timezone for a city or location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name, e.g. 'Seoul' or 'New York'",
                    }
                },
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_currency",
            "description": "Convert an amount from one currency to another using current exchange rates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number", "description": "Amount to convert"},
                    "from_currency": {
                        "type": "string",
                        "description": "3-letter source currency code, e.g. USD",
                    },
                    "to_currency": {
                        "type": "string",
                        "description": "3-letter target currency code, e.g. JPY",
                    },
                },
                "required": ["amount", "from_currency", "to_currency"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_joke",
            "description": "Get a random clean joke to lighten the mood.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_anime",
            "description": "Search for anime or manga information including score, episodes, synopsis, and genres.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Anime or manga title to search for",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search_and_fetch",
            "description": "Search the web for current information and fetch the top result's content. Use for recent events, facts you're unsure about, or anything requiring up-to-date info.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    }
                },
                "required": ["query"],
            },
        },
    },
]

# dispatch table — maps tool name -> (context tag for injection, callable)
TOOL_DISPATCH = {
    "get_weather":          ("weather_data",   lambda **kw: get_weather(kw["location"])),
    "get_timezone":         ("time_data",      lambda **kw: get_timezone(kw["location"])),
    "get_currency":         ("currency_data",  lambda **kw: get_currency(kw["amount"], kw["from_currency"], kw["to_currency"])),
    "get_joke":             ("joke",           lambda **kw: get_joke()),
    "get_anime":            ("anime_data",     lambda **kw: get_anime(kw["query"])),
    "web_search_and_fetch": ("search_results", lambda **kw: web_search_and_fetch(kw["query"])),
}