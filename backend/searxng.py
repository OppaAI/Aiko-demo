"""
backend/searxng.py

Aiko's Modal SearXNG backend.
Deploy: modal deploy backend/search.py
Set SEARXNG_BASE_URL to the Modal endpoint URL in your HF Space secrets.
"""

from asyncio import timeouts
from asyncio import subprocess
from asyncio import timeouts
import modal

app = modal.App("aiko-search")

# ── settings.yml embedded — tune engines to taste ────────────────────────────
SETTINGS_YML = """
use_default_settings: true
server:
  secret_key: "aiko-searxng-secret"
  bind_address: "127.0.0.1:8888"
  limiter: false
  image_proxy: false
  public_instance: false

botdetection:
  ip_limit:
    enabled: false
  ip_lists:
    enabled: false

search:
  safe_search: 0
  autocomplete: ""
  default_lang: "en"
  formats:
    - html
    - json

server:
  secret_key: "aiko-searxng-secret"
  bind_address: "127.0.0.1:8888"
  limiter: false
  image_proxy: false
  public_instance: false

engines:
  - name: duckduckgo
    engine: duckduckgo
    shortcut: ddg
    disabled: false
  - name: brave
    engine: brave
    shortcut: brave
    disabled: false
  - name: wikipedia
    engine: wikipedia
    shortcut: wp
    disabled: false

ui:
  static_use_hash: true

outgoing:
  request_timeout: 8.0
  useragent_suffix: "aiko-search"
"""

# ── image ─────────────────────────────────────────────────────────────────────
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install(
        "git", "build-essential", "libssl-dev", "libffi-dev",
        "python3-dev", "ca-certificates",
    )
    .run_commands(
        "git clone --depth 1 https://github.com/searxng/searxng /searxng",
        "cd /searxng && git init && git config user.email 'aiko@modal.local' && git config user.name 'Aiko' && git commit --allow-empty -m 'init'",
        "pip install -r /searxng/requirements.txt",
        "pip install -e /searxng",
        "mkdir -p /etc/searxng",
        "touch /etc/searxng/limiter.toml",
        "echo '127.0.0.1 localhost' >> /etc/hosts",
        "python3 -c \""
        "import werkzeug.serving, pathlib; "
        "p = pathlib.Path(werkzeug.serving.__file__); "
        "t = p.read_text(); "
        "t = t.replace('socket.gethostbyname(host)', 'host'); "
        "p.write_text(t)"
        "\"",
    )
    .pip_install("httpx", "fastapi[standard]")
    .run_commands(
        f"cat > /etc/searxng/settings.yml << 'YAMLEOF'\n{SETTINGS_YML}\nYAMLEOF",
    )
)

# ── inference class ───────────────────────────────────────────────────────────
@app.cls(
    image=image,
    cpu=1,                    # SearXNG is I/O-bound, no GPU needed
    timeout=60,
    scaledown_window=300,     # keep warm 5 min between requests
)
class AikoSearch:

    @modal.enter()
    def startup(self):
        import threading, os, time, httpx

        os.environ["SEARXNG_SETTINGS_PATH"] = "/etc/searxng/settings.yml"
        os.environ["HOME"] = "/root"
        os.environ["PATH"] = "/usr/local/bin:/usr/bin:/bin"

        # patch werkzeug in-process
        import werkzeug.serving, pathlib, importlib
        p = pathlib.Path(werkzeug.serving.__file__)
        t = p.read_text()
        if "socket.gethostbyname(host)" in t:
            p.write_text(t.replace("socket.gethostbyname(host)", "host"))
            importlib.reload(werkzeug.serving)

        def run():
            from searx.webapp import app
            app.run(host="127.0.0.1", port=8888, debug=False, use_reloader=False)

        threading.Thread(target=run, daemon=True).start()

        time.sleep(8)

        # use /healthz — doesn't trigger botdetection
        for i in range(30):
            try:
                r = httpx.get("http://127.0.0.1:8888/healthz", timeout=3)
                print(f"[aiko-search] healthz status={r.status_code}")
                if r.status_code in (200, 404):  # 404 means Flask answered = it's up
                    print("[aiko-search] SearXNG ready ✓")
                    return
            except Exception as e:
                print(f"[aiko-search] waiting... {e}")
            time.sleep(1)
        raise RuntimeError("SearXNG failed to bind")

    @modal.fastapi_endpoint(method="GET")
    def search(self, q: str, format: str = "json", language: str = "en"):
        import httpx
        resp = httpx.get(
            "http://127.0.0.1:8888/search",
            params={"q": q, "format": format, "language": language},
            headers={"X-Forwarded-For": "1.2.3.4"},
            timeout=20.0,
        )
        print(f"[search] status={resp.status_code} body_len={len(resp.text)} body={resp.text[:300]}")
        if resp.status_code != 200:
            return {"results": [], "error": f"searxng returned {resp.status_code}", "body": resp.text[:300]}
        try:
            return resp.json()
        except Exception as e:
            return {"results": [], "error": str(e), "body": resp.text[:300]}

    @modal.fastapi_endpoint(method="GET")
    def health(self):
        return {"status": "ok", "engine": "searxng"}