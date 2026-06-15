"""
MioTTS on Modal — Aratako/MioTTS-Inference + llama.cpp backend
===============================================================
Architecture:
  1. llama-server  (llama.cpp)      — serves GGUF LLM on :8000 (OpenAI-compatible)
  2. run_server.py (MioTTS-Inference) — synthesis API on :8001

Model: MioTTS-2.6B-Q4_K_M.gguf  (~1.58 GB, fits on A10G)

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
cuda_tag = "12.4.0-runtime-ubuntu22.04"

image = (
    modal.Image.from_registry(f"nvidia/cuda:{cuda_tag}", add_python="3.11")
    .apt_install(
        "git", "curl", "libsndfile1", "ffmpeg", "unzip",
        "cmake", "build-essential", "python3-dev",
    )
    .run_commands(
        # Download prebuilt llama.cpp CUDA binaries from ai-dock/llama.cpp-cuda
        # (official llama.cpp releases don't ship Linux CUDA binaries — only
        # Windows CUDA and Linux CPU/Vulkan). This repo provides ready-to-use
        # tarballs (llama-server + all required .so files) tracking upstream.
        "curl -s https://api.github.com/repos/ai-dock/llama.cpp-cuda/releases/latest"
        " | grep -oE '\"browser_download_url\": \"[^\"]*cuda-12\\.[0-9]+-amd64\\.tar\\.gz\"'"
        " | head -1 | cut -d'\"' -f4 > /tmp/llama_url.txt",
        "cat /tmp/llama_url.txt",
        "curl -L -o /tmp/llama.tar.gz $(cat /tmp/llama_url.txt)",
        "mkdir -p /opt/llama && tar -xzf /tmp/llama.tar.gz -C /opt/llama",
        "find /opt/llama -name 'llama-server' -exec chmod +x {} \\;",
        "find /opt/llama -name '*.so*' -exec dirname {} \\; | sort -u > /etc/ld.so.conf.d/llama.conf",
        "cat /etc/ld.so.conf.d/llama.conf",
        "ldconfig",
        "find /opt/llama -name 'llama-server'",
    )
    # Install uv
    .run_commands("curl -Ls https://astral.sh/uv/install.sh | sh")
    # llama-server binary is already present in this image at /app/llama-server
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
    gpu="A10G",
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
        import os
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = "/app:" + env.get("LD_LIBRARY_PATH", "")

        llama_bin = subprocess.check_output(
            "find /opt/llama -name llama-server -type f | head -1",
            shell=True, text=True
        ).strip()
        if not llama_bin:
            raise RuntimeError("llama-server binary not found under /opt/llama")

        llama_cmd = [
            llama_bin,
            "-m", str(MODELS_DIR / GGUF_FILE),
            "-c", "8192",
            "--cont-batching",
            "--parallel", "4",          # match Modal concurrency
            "--n-gpu-layers", "99",
            "--alias", "miotts",        # avoid model name 404s
            "--host", "0.0.0.0",
            "--port", str(LLAMA_PORT),
        ]
        print("Starting llama-server:", " ".join(llama_cmd))
        self.llama_proc = subprocess.Popen(llama_cmd, env=env)
        _wait_for_port(LLAMA_PORT, "llama-server")

        # 3. Start run_server.py (MioTTS synthesis API)
        presets_dir = MODELS_DIR / "presets"
        presets_dir.mkdir(parents=True, exist_ok=True)
        # Seed with built-in presets (jp_female, jp_male, en_female, en_male)
        # on first run, so custom presets can coexist on the persistent volume.
        subprocess.run(
            "cp -n /opt/miotts/presets/* " + str(presets_dir) + "/ 2>/dev/null || true",
            shell=True,
        )
        volume.commit()
        tts_cmd = [
            "/root/.local/bin/uv", "run",
            "python", "run_server.py",
            "--llm-base-url", f"http://localhost:{LLAMA_PORT}/v1",
            "--host", "0.0.0.0",
            "--port", str(TTS_PORT),
            "--presets-dir", str(presets_dir),
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
# Register a named voice preset from reference audio
#
# Usage:
#   modal run backend/miotts.py::register_preset \
#       --audio-path /path/to/Aiko.wav --preset-id Aiko
#
# After this completes, the running server's volume will contain
# /models/presets/Aiko.* (pre-encoded reference). Restart the app (or wait
# for the container to scale down/up) so run_server.py picks up the new
# preset, then use reference_preset_id=Aiko / {"type":"preset","preset_id":"Aiko"}.
# ---------------------------------------------------------------------------
@app.function(
    gpu="T4",
    image=image,
    volumes={str(MODELS_DIR): volume},
    timeout=10 * MINUTES,
)
def register_preset(audio_bytes: bytes, audio_filename: str, preset_id: str):
    import subprocess as sp

    presets_dir = MODELS_DIR / "presets"
    presets_dir.mkdir(parents=True, exist_ok=True)

    # Seed built-in presets too, in case this runs before the server ever has.
    sp.run(
        f"cp -n /opt/miotts/presets/* {presets_dir}/ 2>/dev/null || true",
        shell=True,
    )

    # Write the uploaded reference audio into the container's filesystem.
    local_audio = Path("/tmp") / audio_filename
    local_audio.write_bytes(audio_bytes)

    cmd = [
        "/root/.local/bin/uv", "run", "python", "scripts/generate_preset.py",
        "--audio", str(local_audio),
        "--preset-id", preset_id,
        "--output-dir", str(presets_dir),
    ]
    print("Running:", " ".join(cmd))
    sp.run(cmd, cwd="/opt/miotts", check=True)

    volume.commit()
    print(f"Preset '{preset_id}' registered in {presets_dir}")
    print("Files:", list(presets_dir.glob(f"{preset_id}*")))


@app.local_entrypoint()
def register_preset_cli(audio_path: str, preset_id: str):
    """
    Usage:
      modal run backend/miotts.py::register_preset_cli \\
          --audio-path /local/path/to/Aiko.wav --preset-id Aiko
    """
    data = Path(audio_path).read_bytes()
    register_preset.remote(data, Path(audio_path).name, preset_id)


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