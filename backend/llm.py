"""
backend/llm.py

Aiko's Modal LLM backend — runs llama.cpp server with Ministral 3B Q4 on GPU.
Deploy with: modal deploy backend/llm.py
OpenAI-compatible endpoint — think.py needs zero changes.
Set LLAMA_BASE_URL to the Modal chat URL in your HF Space secrets.
"""

import os
import modal

# ── app + volume ──────────────────────────────────────────────────────────────

app    = modal.App("aiko-llm")
volume = modal.Volume.from_name("aiko-models", create_if_missing=True)

# ── image ─────────────────────────────────────────────────────────────────────

image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.1.0-devel-ubuntu22.04",
        add_python="3.11"
    )
    .apt_install(
        "curl", "ca-certificates", "git",
        "build-essential", "cmake", "libcurl4-openssl-dev"
    )
    .run_commands(
        "git clone https://github.com/ggerganov/llama.cpp /llama.cpp",
        "cd /llama.cpp && cmake -B build -DLLAMA_CURL=ON -DGGML_CUDA=ON "
        "-DCMAKE_CUDA_ARCHITECTURES=75 "
        "-DCMAKE_EXE_LINKER_FLAGS='-L/usr/local/cuda/lib64/stubs -lcuda' "
        "-DCMAKE_SHARED_LINKER_FLAGS='-L/usr/local/cuda/lib64/stubs -lcuda' "
        "&& cmake --build build --config Release -j$(nproc) -t llama-server",
        "cp /llama.cpp/build/bin/llama-server /usr/local/bin/llama-server",
    )
    .pip_install("huggingface_hub", "httpx", "fastapi[standard]")
)

# ── constants ─────────────────────────────────────────────────────────────────

#HF_REPO    = "unsloth/Ministral-3-3B-Instruct-2512-GGUF"
#HF_FILE    = "Ministral-3-3B-Instruct-2512-UD-Q4_K_XL.gguf"
#MODEL_PATH = f"/models/{HF_FILE}"
HF_REPO = "unsloth/Ministral-3-8B-Instruct-2512-GGUF"
HF_FILE = "Ministral-3-8B-Instruct-2512-UD-Q4_K_XL.gguf"
MODEL_PATH = f"/models/{HF_FILE}"
LLAMA_PORT = 8080

# ── inference class ───────────────────────────────────────────────────────────

@app.cls(
    image=image,
    gpu="T4",
    volumes={"/models": volume},
    timeout=300,
    scaledown_window=300,
    secrets=[modal.Secret.from_name("aiko-secrets")],
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
            volume.commit()  # persist to volume after download
            print("[aiko] model cached ✓")
        else:
            print("[aiko] model already cached, skipping download")

        # ── start llama.cpp server ────────────────────────────────────────────
        # --jinja enables the model's chat template (incl. tool-calling format
        # for Ministral) so `tools` / `tool_choice` in requests are honored and
        # the response can contain `tool_calls`.
        self._proc = subprocess.Popen([
            "/usr/local/bin/llama-server",
            "--model",        MODEL_PATH,
            "--port",         str(LLAMA_PORT),
            "--host",         "0.0.0.0",
            "--n-gpu-layers", "99",
            "--ctx-size",     "4096",
            "--threads",      "4",
            "--parallel",     "1",
            "--jinja",
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

    @modal.fastapi_endpoint(method="POST")
    def chat(self, request: dict):
        import httpx
        resp = httpx.post(
            f"http://localhost:{LLAMA_PORT}/v1/chat/completions",
            json=request,
            timeout=120.0,
        )
        return resp.json()

    @modal.fastapi_endpoint(method="GET")
    def health(self):
        return {"status": "ok", "model": HF_FILE}