"""
backend/llm.py

Aiko's Modal LLM backend — runs llama.cpp server with Ministral 3B Q4 on GPU.
Deploy with: modal deploy backend/llm.py
The web endpoint is OpenAI-compatible, so think.py needs zero changes.
Just set LLAMA_BASE_URL to the Modal URL in your HF Space secrets.
"""

import os
import modal

# ── app + volume ──────────────────────────────────────────────────────────────

app    = modal.App("aiko-llm")
volume = modal.Volume.from_name("aiko-models", create_if_missing=True)

# ── image ─────────────────────────────────────────────────────────────────────

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("curl", "ca-certificates")
    .run_commands(
        # grab the latest llama.cpp server binary
        "curl -L https://github.com/ggerganov/llama.cpp/releases/latest/download/llama-server-linux-x64 "
        "-o /usr/local/bin/llama-server && chmod +x /usr/local/bin/llama-server"
    )
    .pip_install("huggingface_hub", "httpx")
)

# ── constants ─────────────────────────────────────────────────────────────────

HF_REPO    = "unsloth/Ministral-3-3B-Instruct-2512-GGUF"
HF_FILE    = "Ministral-3-3B-Instruct-2512-UD-Q4_K_XL.gguf"
MODEL_PATH = f"/models/{HF_FILE}"
LLAMA_PORT = 8080

# ── inference class ───────────────────────────────────────────────────────────

@app.cls(
    image=image,
    gpu="T4",                        # cheapest Modal GPU, plenty for 3B Q4
    volumes={"/models": volume},
    timeout=300,
    container_idle_timeout=120,      # stays warm 2 min between requests
    secrets=[modal.Secret.from_name("aiko-secrets")],  # optional HF_TOKEN if needed
)
class AikoLLM:

    @modal.enter()
    def startup(self):
        import subprocess, time, httpx
        from huggingface_hub import hf_hub_download

        # ── pull model once, cache in volume ──────────────────────────────────
        if not os.path.exists(MODEL_PATH):
            print(f"[aiko] downloading {HF_FILE} from HF...")
            hf_hub_download(
                repo_id=HF_REPO,
                filename=HF_FILE,
                local_dir="/models",
            )
            print("[aiko] model cached ✓")
        else:
            print("[aiko] model already cached, skipping download")

        # ── start llama.cpp server ────────────────────────────────────────────
        self._proc = subprocess.Popen([
            "/usr/local/bin/llama-server",
            "--model",          MODEL_PATH,
            "--port",           str(LLAMA_PORT),
            "--host",           "0.0.0.0",
            "--n-gpu-layers",   "99",    # full GPU offload
            "--ctx-size",       "4096",
            "--threads",        "4",
            "--parallel",       "1",
        ])

        # ── wait for server ready ─────────────────────────────────────────────
        for i in range(60):
            try:
                r = httpx.get(f"http://localhost:{LLAMA_PORT}/health", timeout=2)
                if r.status_code == 200:
                    print("[aiko] llama.cpp ready ✓")
                    break
            except Exception:
                pass
            time.sleep(1)
        else:
            raise RuntimeError("llama.cpp server failed to start")

    @modal.web_endpoint(method="POST")
    def chat(self, request: dict):
        """OpenAI-compatible /v1/chat/completions proxy."""
        import httpx
        resp = httpx.post(
            f"http://localhost:{LLAMA_PORT}/v1/chat/completions",
            json=request,
            timeout=120.0,
        )
        return resp.json()

    @modal.web_endpoint(method="GET")
    def health(self):
        return {"status": "ok", "model": HF_FILE}