"""
core/tools.py
Aiko's tool belt — web search, weather, timezone, currency, crypto, jokes, anime info.
All tools return plain strings ready for context injection into the system prompt.
No API keys required — all free/no-auth endpoints.
Tools:
  web_search(query)            — SearXNG JSON API (Modal-hosted)
  web_fetch(url)               — raw page fetch + HTML strip
  web_search_and_fetch(query)  — search + fetch top result, combined string
  get_weather(location)        — Open-Meteo geocoding + weather API (no key)
  get_timezone(location)       — worldtimeapi.org (no key)
  get_currency(amount, fr, to) — Frankfurter API (no key, ECB data)
  get_crypto_price(coin, currency) — CoinGecko API (no key)
  get_joke()                   — JokeAPI (no key)
  get_anime(query)             — Jikan API / MyAnimeList (no key)
Intent detection (used by think.py as fallback when LLM tool-calling
doesn't produce a tool_call):
  is_weather_intent(text)
  is_timezone_intent(text)
  is_currency_intent(text)
  is_crypto_intent(text)
  is_joke_intent(text)
  is_anime_intent(text)
  is_search_intent(text)
LLM-driven tool calling (preferred path, used by think.py):
  TOOL_SCHEMAS   — OpenAI function-calling spec for all tools
  TOOL_DISPATCH  — maps tool name -> (context_tag, callable)
Environment variables:
  SEARXNG_BASE_URL — full URL of your Modal SearXNG search endpoint, e.g.
                     https://oppa-ai-org--aiko-search-aikosearch-search.modal.run
"""

import os
import re
import time
import httpx

# ── config ────────────────────────────────────────────────────────────────────

# Full URL to the SearXNG "search" endpoint itself (NOT a base path — do not
# append "/search", the Modal fastapi_endpoint root IS the search route).
SEARXNG_BASE_URL = os.getenv("SEARXNG_BASE_URL")
if not SEARXNG_BASE_URL:
    raise RuntimeError("SEARXNG_BASE_URL is not set")

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

_CRYPTO_TRIGGERS = re.compile(
    r"\b(bitcoin|btc|ethereum|eth|crypto|cryptocurrency|dogecoin|doge|"
    r"solana|sol|litecoin|ltc|xrp|ripple|cardano|ada)\b"
    r".*\b(price|worth|value|cost|trading|rate)\b"
    r"|\b(price|worth|value|cost)\b"
    r".*\b(bitcoin|btc|ethereum|eth|crypto|dogecoin|doge|solana|sol|"
    r"litecoin|ltc|xrp|ripple|cardano|ada)\b",
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

_CAMERA_SEE_TRIGGERS = re.compile(
    r"\b(look at (?:this|me|something)|see what|what(?: can)? you see|"
    r"look around|open (?:the )?camera|take a (?:photo|picture|shot)|"
    r"what's in front of you|can you see)\b",
    re.IGNORECASE,
)


def is_search_intent(text: str)   -> bool: return bool(_SEARCH_TRIGGERS.search(text))
def is_weather_intent(text: str)  -> bool: return bool(_WEATHER_TRIGGERS.search(text))
def is_timezone_intent(text: str) -> bool: return bool(_TIMEZONE_TRIGGERS.search(text))
def is_currency_intent(text: str) -> bool: return bool(_CURRENCY_TRIGGERS.search(text))
def is_crypto_intent(text: str)   -> bool: return bool(_CRYPTO_TRIGGERS.search(text))
def is_joke_intent(text: str)     -> bool: return bool(_JOKE_TRIGGERS.search(text))
def is_anime_intent(text: str)    -> bool: return bool(_ANIME_TRIGGERS.search(text))
def is_camera_see_intent(text: str) -> bool: return bool(_CAMERA_SEE_TRIGGERS.search(text))



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
    # strip common question prefixes — order matters: longest patterns first
    cleaned = re.sub(
        r"^(what time is it|what(?:'s| is) the (?:weather|temperature|forecast|time|local time)"
        r"|how(?:'s| is) the weather|how(?:'s| is) the temperature"
        r"|what(?:'s| is) (?:the )?(?:current )?(?:weather|temperature|forecast|time|local time)"
        r"|(?:current |local )?(?:weather|forecast|time|timezone)"
        r"|tell me the (?:weather|time|temperature)"
        r"|check the (?:weather|time)"
        r"|do you know what time it is"
        r"|what time do they have)\s*",
        "", text, flags=re.IGNORECASE,
    ).strip()
    # strip prepositions and trailing punctuation
    cleaned = re.sub(r"^(in|at|for|of|around|near|over)\s+", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"[\s?!.,;]+$", "", cleaned).strip()
    # strip trailing/standalone noise like "right now", "currently", "today"
    cleaned = re.sub(r"(?:^|\s+)(right now|currently|today|now|rn)$", "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned or ""


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


_CRYPTO_NAME_MAP = {
    "btc": "bitcoin", "bitcoin": "bitcoin",
    "eth": "ethereum", "ethereum": "ethereum",
    "doge": "dogecoin", "dogecoin": "dogecoin",
    "sol": "solana", "solana": "solana",
    "ltc": "litecoin", "litecoin": "litecoin",
    "xrp": "ripple", "ripple": "ripple",
    "ada": "cardano", "cardano": "cardano",
}


def extract_crypto_parts(text: str) -> tuple[str, str]:
    """
    Parse coin + target fiat currency from natural language.
    Returns (coingecko_coin_id, currency_code).
    Defaults: ("bitcoin", "usd").
    """
    text_lower = text.lower()

    coin = "bitcoin"
    for key, coingecko_id in _CRYPTO_NAME_MAP.items():
        if re.search(rf"\b{re.escape(key)}\b", text_lower):
            coin = coingecko_id
            break

    currency = "usd"
    currency_match = re.search(
        r"\b(usd|eur|jpy|gbp|krw|cad|aud|sgd|thb)\b", text_lower
    )
    if currency_match:
        currency = currency_match.group(1)

    return coin, currency


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
    """Search via SearXNG JSON API (Modal-hosted). Falls back to error string on failure."""
    if not SEARXNG_BASE_URL:
        return "[search unavailable: SEARXNG_BASE_URL not set]"
    query = query.strip().strip("'\"")
    try:
        resp = httpx.get(
            SEARXNG_BASE_URL,
            params={"q": query, "format": "json", "language": "en"},
            timeout=15,
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

# WMO weather code → human-readable description
_WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    56: "Light freezing drizzle", 57: "Dense freezing drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    66: "Light freezing rain", 67: "Heavy freezing rain",
    71: "Slight snowfall", 73: "Moderate snowfall", 75: "Heavy snowfall",
    77: "Snow grains", 80: "Slight rain showers", 81: "Moderate rain showers",
    82: "Violent rain showers", 85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def get_weather(location: str) -> str:
    """
    Fetch current weather via Open-Meteo (no API key needed).
    Uses their geocoding API for accurate city resolution, then
    fetches current conditions by lat/lon.
    """
    try:
        # Step 1: Geocode the location name → lat/lon
        geo_resp = httpx.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": location, "count": 1, "language": "en"},
            timeout=10,
        )
        geo_resp.raise_for_status()
        geo_results = geo_resp.json().get("results")
        if not geo_results:
            return f"[weather: location not found for '{location}']"

        place = geo_results[0]
        lat   = place["latitude"]
        lon   = place["longitude"]
        city  = place.get("name", location)
        country = place.get("country", "")

        # Step 2: Fetch current weather by coordinates
        weather_resp = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude":  lat,
                "longitude": lon,
                "current":   "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
                "temperature_unit": "celsius",
                "wind_speed_unit":  "kmh",
            },
            timeout=10,
        )
        weather_resp.raise_for_status()
        current = weather_resp.json().get("current", {})

        temp_c   = current.get("temperature_2m")
        feels_c  = current.get("apparent_temperature")
        humidity = current.get("relative_humidity_2m")
        wind     = current.get("wind_speed_10m")
        code     = current.get("weather_code", -1)
        desc     = _WMO_CODES.get(code, "Unknown")

        # Convert C to F for display
        temp_f = round(temp_c * 9 / 5 + 32, 1) if temp_c is not None else "?"

        return (
            f"[Weather for {city}, {country}]\n"
            f"Condition : {desc}\n"
            f"Temp      : {temp_c}°C / {temp_f}°F (feels like {feels_c}°C)\n"
            f"Humidity  : {humidity}%\n"
            f"Wind      : {wind} km/h"
        )
    except Exception as e:
        return f"[weather fetch failed: {e}]"


# ── timezone ──────────────────────────────────────────────────────────────────

def get_timezone(location: str) -> str:
    from datetime import datetime
    from zoneinfo import ZoneInfo
    import re

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
        "vancouver": "America/Vancouver",
    }

    loc_clean = location.lower().strip()
    tz_name = None

    # 1. Exact map check
    if loc_clean in _CITY_MAP:
        tz_name = _CITY_MAP[loc_clean]

    if not tz_name:
        try:
            import zoneinfo
            all_zones = zoneinfo.available_timezones()

            # 2. Match full string with underscores in timezone name
            loc_underscore = loc_clean.replace(" ", "_")
            matches = [z for z in all_zones if loc_underscore in z.lower()]
            if matches:
                tz_name = matches[0]

            # 3. Handle region/country suffixes (e.g. "Tokyo, Japan" -> "Tokyo")
            if not tz_name and "," in loc_clean:
                city_part = loc_clean.split(",")[0].strip()
                if city_part in _CITY_MAP:
                    tz_name = _CITY_MAP[city_part]
                else:
                    city_underscore = city_part.replace(" ", "_")
                    matches = [z for z in all_zones if city_underscore in z.lower()]
                    if matches:
                        tz_name = matches[0]

            # 4. Fallback: match sub-phrases of words
            if not tz_name:
                words = [w for w in re.split(r"[\s,;_]+", loc_clean) if w]
                # Prioritize exact match with the city component of the zone
                for length in range(len(words), 0, -1):
                    for i in range(len(words) - length + 1):
                        phrase = "_".join(words[i : i + length])
                        if len(phrase) > 2:
                            matches = [z for z in all_zones if z.lower().split("/")[-1] == phrase]
                            if matches:
                                tz_name = matches[0]
                                break
                    if tz_name:
                        break

                # Fallback to substring match on city component (excluding common words)
                if not tz_name:
                    for length in range(len(words), 0, -1):
                        for i in range(len(words) - length + 1):
                            phrase = "_".join(words[i : i + length])
                            if len(phrase) > 2:
                                if phrase in {"the", "what", "time", "date", "local", "zone", "city"}:
                                    continue
                                matches = [z for z in all_zones if phrase in z.lower().split("/")[-1]]
                                if matches:
                                    tz_name = matches[0]
                                    break
                        if tz_name:
                            break
        except Exception:
            pass

    if not tz_name:
        return f"[timezone not found for: {location}]"

    try:
        now = datetime.now(ZoneInfo(tz_name))
        day_name = now.strftime("%A")
        return (
            f"[Time in {location.title()}]\n"
            f"Local time : {now.strftime('%Y-%m-%d %H:%M:%S')} ({day_name})\n"
            f"Timezone   : {tz_name}\n"
            f"UTC offset : {now.strftime('%z')}"
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


# ── crypto ────────────────────────────────────────────────────────────────────

def get_crypto_price(coin: str, currency: str = "usd") -> str:
    """
    Fetch current crypto price via CoinGecko's free API (no key needed).
    `coin` should be a CoinGecko coin id, e.g. 'bitcoin', 'ethereum', 'dogecoin'.
    `currency` is a fiat code, e.g. 'usd', 'cad', 'eur', 'jpy'.
    """
    coin     = coin.strip().lower()
    currency = currency.strip().lower()
    try:
        resp = httpx.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={
                "ids": coin,
                "vs_currencies": currency,
                "include_24hr_change": "true",
            },
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        resp.raise_for_status()
        data = resp.json()
        coin_data = data.get(coin)

        if not coin_data or currency not in coin_data:
            return f"[crypto price not found for {coin} in {currency.upper()}]"

        price  = coin_data[currency]
        change = coin_data.get(f"{currency}_24h_change")

        lines = [
            f"[Crypto price — {coin.upper()}]",
            f"1 {coin.upper()} = {price:,.2f} {currency.upper()}",
        ]
        if change is not None:
            direction = "▲" if change >= 0 else "▼"
            lines.append(f"24h change: {direction} {change:.2f}%")

        return "\n".join(lines)
    except Exception as e:
        return f"[crypto price fetch failed: {e}]"


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


def capture_camera_image(prompt: str = "Describe what you see in detail.") -> str:
    """
    Signal the frontend to auto-open the camera/image modal so Aiko can
    see.  Returns a machine-readable marker that app.py intercepts before
    the LLM response reaches the user.
    """
    return "__OPEN_CAMERA__"


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
            "description": "Convert an amount from one fiat currency to another using current exchange rates.",
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
            "name": "get_crypto_price",
            "description": "Get the current price of a cryptocurrency (e.g. Bitcoin, Ethereum) in a given fiat currency. Use this instead of web search for crypto price questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "coin": {
                        "type": "string",
                        "description": "CoinGecko coin id, e.g. 'bitcoin', 'ethereum', 'dogecoin', 'solana'",
                    },
                    "currency": {
                        "type": "string",
                        "description": "3-letter fiat currency code, e.g. usd, cad, eur, jpy. Defaults to usd.",
                    },
                },
                "required": ["coin"],
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
    {
        "type": "function",
        "function": {
            "name": "capture_camera_image",
            "description": "Capture a live image from Aiko's camera/webcam and describe what she sees in front of her.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Optional specific question or prompt about the image, e.g. 'What color is my shirt?' or 'Describe what you see in detail.'",
                    }
                },
            },
        },
    },
]

# dispatch table — maps tool name -> (context tag for injection, callable)
TOOL_DISPATCH = {
    "get_weather":          ("weather_data",   lambda **kw: get_weather(kw["location"])),
    "get_timezone":         ("time_data",      lambda **kw: get_timezone(kw["location"])),
    "get_currency":         ("currency_data",  lambda **kw: get_currency(kw["amount"], kw["from_currency"], kw["to_currency"])),
    "get_crypto_price":     ("crypto_data",    lambda **kw: get_crypto_price(kw["coin"], kw.get("currency", "usd"))),
    "get_joke":             ("joke",           lambda **kw: get_joke()),
    "get_anime":            ("anime_data",     lambda **kw: get_anime(kw["query"])),
    "web_search_and_fetch": ("search_results", lambda **kw: web_search_and_fetch(kw["query"])),
    "capture_camera_image": ("camera_view",    lambda **kw: capture_camera_image(kw.get("prompt", "Describe what you see in detail."))),
}