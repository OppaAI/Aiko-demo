"""
MioTTS on Modal — Aratako/MioTTS-Inference + llama.cpp backend
===============================================================
Architecture:
  1. llama-server  (llama.cpp)      — serves GGUF LLM on :8000 (OpenAI-compatible)
  2. run_server.py (MioTTS-Inference) — synthesis API on :8001

Model: MioTTS-2.6B-Q4_K_M.gguf  (~1.58 GB, fits on T4)

Deploy:
  modal deploy backend/miotts.py

One-off test:
  modal run backend/miotts.py

Synthesis API (after deploy):
  curl -X POST https://<workspace>--miotts-ttsserver-serve.modal.run/synthesize \
       -H "Content-Type: application/json" \
       -d '{"text": "Hello from Modal!"}' \
       --output speech.wav

  # With a voice preset (register first via /presets endpoint):
  -d '{"text": "Hello!", "preset_id": "my_voice"}'
"""

import subprocess
import sys
import time
from pathlib import Path

import modal

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
GGUF_REPO     = "Aratako/MioTTS-GGUF"
GGUF_FILE     = "MioTTS-2.6B-Q4_K_M.gguf"

LLAMA_PORT    = 8000   # llama-server OpenAI-compatible API
TTS_PORT      = 8001   # MioTTS-Inference run_server.py
MINUTES       = 60

# ---------------------------------------------------------------------------
# Shared volume — model file downloaded once, reused on warm containers
# ---------------------------------------------------------------------------
volume = modal.Volume.from_name("miotts-models", create_if_missing=True)
MODELS_DIR = Path("/models")

# ---------------------------------------------------------------------------
# Container image
# ---------------------------------------------------------------------------
cuda_tag = "12.4.0-devel-ubuntu22.04"

image = (
    modal.Image.from_registry(f"nvidia/cuda:{cuda_tag}", add_python="3.11")
    .apt_install(
        "git", "cmake", "build-essential", "ninja-build", "curl",
        "libsndfile1", "ffmpeg",
    )
    # Install uv
    .run_commands("curl -Ls https://astral.sh/uv/install.sh | sh")
    # Build llama.cpp with CUDA so we get llama-server.
    # LLAMA_BUILD_SERVER_WEBUI=OFF skips the UI asset embedding step that
    # fails when the HuggingFace CDN returns a partial/empty build.json,
    # which causes a zero-size array compile error in the generated ui.cpp.
    .run_commands(
        "git clone --depth 1 https://github.com/ggml-org/llama.cpp /opt/llama.cpp",
        # Symlink libcuda.so.1 stub — devel image ships .so but not .so.1
        "ln -sf /usr/local/cuda/lib64/stubs/libcuda.so /usr/local/cuda/lib64/stubs/libcuda.so.1",
        "cmake /opt/llama.cpp -B /opt/llama.cpp/build"
        " -DGGML_CUDA=ON"
        " -DCMAKE_BUILD_TYPE=Release"
        " -DLLAMA_BUILD_SERVER_WEBUI=OFF"
        " -DCMAKE_EXE_LINKER_FLAGS='-L/usr/local/cuda/lib64/stubs -Wl,-rpath,/usr/local/cuda/lib64'",
        "cmake --build /opt/llama.cpp/build --config Release -j$(nproc) --target llama-server",
    )
    # Clone MioTTS-Inference and install its Python deps
    .run_commands(
        "git clone https://github.com/Aratako/MioTTS-Inference.git /opt/miotts",
        "cd /opt/miotts && /root/.local/bin/uv sync",
        # flash-attn is recommended but slow to build; skip for now, add if needed:
        # "cd /opt/miotts && MAX_JOBS=4 /root/.local/bin/uv pip install --no-build-isolation flash-attn",
    )
    .pip_install("huggingface_hub")
)

app = modal.App("miotts", image=image)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _download_gguf():
    from huggingface_hub import hf_hub_download
    dest = MODELS_DIR / GGUF_FILE
    if not dest.exists():
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        print(f"Downloading {GGUF_FILE} ...")
        hf_hub_download(repo_id=GGUF_REPO, filename=GGUF_FILE, local_dir=str(MODELS_DIR))
        print("Download complete.")
    else:
        print(f"Model already cached: {dest}")


def _wait_for_port(port: int, label: str, timeout: int = 120):
    import httpx
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(f"http://localhost:{port}/health", timeout=2)
            if r.status_code == 200:
                print(f"{label} is ready on :{port}")
                return
        except Exception:
            pass
        time.sleep(2)
    raise RuntimeError(f"{label} did not become ready within {timeout}s")


# ---------------------------------------------------------------------------
# Modal class
# ---------------------------------------------------------------------------
@app.cls(
    gpu="T4",
    timeout=10 * MINUTES,
    scaledown_window=5 * MINUTES,
    min_containers=0,
    volumes={str(MODELS_DIR): volume},
)
@modal.concurrent(max_inputs=4)
class TTSServer:

    @modal.enter()
    def startup(self):
        # 1. Download GGUF (no-op if already cached)
        _download_gguf()
        volume.commit()

        # 2. Start llama-server
        llama_cmd = [
            "/opt/llama.cpp/build/bin/llama-server",
            "-m", str(MODELS_DIR / GGUF_FILE),
            "-c", "8192",
            "--cont-batching",
            "--batch-size", "8",
            "--n-gpu-layers", "99",   # offload all layers to GPU
            "--host", "0.0.0.0",
            "--port", str(LLAMA_PORT),
        ]
        print("Starting llama-server:", " ".join(llama_cmd))
        self.llama_proc = subprocess.Popen(llama_cmd)
        _wait_for_port(LLAMA_PORT, "llama-server")

        # 3. Start run_server.py (MioTTS synthesis API)
        tts_cmd = [
            "/root/.local/bin/uv", "run",
            "python", "run_server.py",
            "--llm-base-url", f"http://localhost:{LLAMA_PORT}/v1",
            "--host", "0.0.0.0",
            "--port", str(TTS_PORT),
        ]
        print("Starting MioTTS run_server.py:", " ".join(tts_cmd))
        self.tts_proc = subprocess.Popen(tts_cmd, cwd="/opt/miotts")
        _wait_for_port(TTS_PORT, "MioTTS run_server")

    @modal.exit()
    def teardown(self):
        for proc in (self.tts_proc, self.llama_proc):
            try:
                proc.terminate()
            except Exception:
                pass

    @modal.web_server(port=TTS_PORT, startup_timeout=5 * MINUTES)
    def serve(self):
        # MioTTS run_server.py is already running on TTS_PORT.
        # Modal just forwards incoming HTTP traffic to it.
        pass


# ---------------------------------------------------------------------------
# Quick smoke test:  modal run backend/miotts.py
# ---------------------------------------------------------------------------
@app.local_entrypoint()
def main():
    import httpx
    from pathlib import Path

    server = TTSServer()
    server.startup.local()

    try:
        resp = httpx.post(
            f"http://localhost:{TTS_PORT}/synthesize",
            json={"text": "Hello from Modal!"},
            timeout=60,
        )
        resp.raise_for_status()
        out = Path("/tmp/miotts_test.wav")
        out.write_bytes(resp.content)
        print(f"✓ {len(resp.content)} bytes → {out}")
    finally:
        server.teardown.local()