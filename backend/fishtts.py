"""
Fish Speech S2-Pro on Modal
============================
Architecture:
  tools/api_server.py (fish-speech) — TTS API on :8080

Model: fishaudio/s2-pro (~8GB on disk, needs A100 40GB)

Deploy:
  modal deploy backend/fish_tts.py

One-off test:
  modal run backend/fish_tts.py

API:
  POST /v1/tts
    - multipart/form-data with fields: text, reference_id (optional),
      reference_audio (optional file), reference_text (optional)
    - returns: audio/wav stream

Health:
  GET /v1/health
"""

import subprocess
import time
from pathlib import Path

import modal

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
HF_REPO       = "fishaudio/s2-pro"
CHECKPOINTS   = Path("/models/checkpoints/s2-pro")
TTS_PORT      = 8080
MINUTES       = 60

# ---------------------------------------------------------------------------
# Shared volume — model weights downloaded once, reused on warm containers
# ---------------------------------------------------------------------------
volume = modal.Volume.from_name("fish-tts-models", create_if_missing=True)
MODELS_DIR = Path("/models")

# ---------------------------------------------------------------------------
# Container image
# ---------------------------------------------------------------------------
image = (
    modal.Image.from_registry("nvidia/cuda:12.4.0-runtime-ubuntu22.04", add_python="3.11")
    .apt_install(
        "git", "curl", "libsndfile1", "ffmpeg", "build-essential",
        "portaudio19-dev", "clang",
    )
    .run_commands(
        # Clone fish-speech at v1.5.1 (last stable before S2-Pro refactor)
        # but use main for S2-Pro since v1.5.1 predates it.
        "git clone --depth 1 https://github.com/fishaudio/fish-speech.git /opt/fish-speech",
    )
    .pip_install(
        "torch==2.4.1", "torchvision", "torchaudio",
        extra_index_url="https://download.pytorch.org/whl/cu124",
    )
    .run_commands(
        # Install fish-speech dependencies
        "pip install -e /opt/fish-speech",
    )
    .pip_install("huggingface_hub")
)

app = modal.App("fish-tts", image=image)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _download_model():
    from huggingface_hub import snapshot_download
    if not CHECKPOINTS.exists() or not any(CHECKPOINTS.iterdir()):
        CHECKPOINTS.mkdir(parents=True, exist_ok=True)
        print(f"Downloading {HF_REPO} ...")
        snapshot_download(repo_id=HF_REPO, local_dir=str(CHECKPOINTS))
        print("Download complete.")
    else:
        print(f"Model already cached: {CHECKPOINTS}")


def _wait_for_port(port: int, label: str, timeout: int = 180):
    import httpx
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(f"http://localhost:{port}/v1/health", timeout=2)
            if r.status_code == 200:
                print(f"{label} is ready on :{port}")
                return
        except Exception:
            pass
        time.sleep(2)
    raise RuntimeError(f"{label} did not become ready within {timeout}s")


# ---------------------------------------------------------------------------
# Modal class — A100 40GB for S2-Pro (4B model, ~8GB weights + activations)
# ---------------------------------------------------------------------------
@app.cls(
    gpu="T4",
    timeout=10 * MINUTES,
    scaledown_window=5 * MINUTES,
    min_containers=0,
    volumes={str(MODELS_DIR): volume},
)
@modal.concurrent(max_inputs=4)
class FishTTSServer:

    @modal.enter()
    def startup(self):
        # 1. Download model weights (no-op if already cached)
        _download_model()
        volume.commit()

        # 2. Start api_server.py
        cmd = [
            "python", "/opt/fish-speech/tools/api_server.py",
            "--llama-checkpoint-path", str(CHECKPOINTS),
            "--decoder-checkpoint-path", str(CHECKPOINTS / "codec.pth"),
            "--listen", f"0.0.0.0:{TTS_PORT}",
            "--half",   # fp16 to save VRAM
        ]
        print("Starting Fish Speech API server:", " ".join(cmd))
        self.proc = subprocess.Popen(cmd)
        _wait_for_port(TTS_PORT, "Fish Speech API server")

    @modal.exit()
    def teardown(self):
        try:
            self.proc.terminate()
        except Exception:
            pass

    @modal.web_server(port=TTS_PORT, startup_timeout=5 * MINUTES)
    def serve(self):
        # api_server.py is already running on TTS_PORT.
        # Modal forwards incoming HTTP traffic to it.
        pass


# ---------------------------------------------------------------------------
# Register a named voice reference (for --reference_id in TTS requests)
#
# Usage:
#   modal run backend/fish_tts.py::register_voice_cli \
#       --audio-path ./Aiko.wav --reference-id Aiko --reference-text "こんにちは"
#
# After this, use reference_id=Aiko in requests (no re-upload needed).
# ---------------------------------------------------------------------------
@app.function(
    gpu="T4",
    image=image,
    volumes={str(MODELS_DIR): volume},
    timeout=10 * MINUTES,
)
def register_voice(audio_bytes: bytes, audio_filename: str, reference_id: str, reference_text: str = ""):
    import subprocess as sp

    voices_dir = MODELS_DIR / "voices" / reference_id
    voices_dir.mkdir(parents=True, exist_ok=True)

    # Write audio file
    audio_path = voices_dir / audio_filename
    audio_path.write_bytes(audio_bytes)

    # Write reference text if provided
    if reference_text:
        (voices_dir / "text.txt").write_text(reference_text)

    # Encode reference audio to VQ tokens using the VQ encoder
    encoded_path = voices_dir / "encoded.npy"
    encode_cmd = [
        "python", "/opt/fish-speech/tools/vqgan/encode_audio.py",
        "--input", str(audio_path),
        "--output", str(encoded_path),
        "--checkpoint", str(CHECKPOINTS / "codec.pth"),
    ]
    print("Encoding reference audio:", " ".join(encode_cmd))
    result = sp.run(encode_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # Fallback: just store the wav — api_server supports raw audio too
        print("VQ encode failed (may not be needed), storing raw wav.")
        print(result.stderr)
    else:
        print("Encoded successfully.")

    volume.commit()
    print(f"Voice '{reference_id}' registered at {voices_dir}")
    print("Files:", list(voices_dir.iterdir()))


@app.local_entrypoint()
def register_voice_cli(audio_path: str, reference_id: str, reference_text: str = ""):
    """
    Usage:
      modal run backend/fish_tts.py::register_voice_cli \\
          --audio-path ./Aiko.wav --reference-id Aiko --reference-text "こんにちは"
    """
    data = Path(audio_path).read_bytes()
    register_voice.remote(data, Path(audio_path).name, reference_id, reference_text)


# ---------------------------------------------------------------------------
# Quick smoke test: modal run backend/fish_tts.py
# ---------------------------------------------------------------------------
@app.local_entrypoint()
def main():
    import httpx, base64
    from pathlib import Path

    url = "https://oppa-ai-org--fish-tts-fishttserver-serve.modal.run/v1/tts"
    resp = httpx.post(
        url,
        data={"text": "こんにちは、魚の音声です。"},
        timeout=120,
    )
    resp.raise_for_status()
    out = Path("/tmp/fish_tts_test.wav")
    out.write_bytes(resp.content)
    print(f"✓ {len(resp.content)} bytes → {out}")