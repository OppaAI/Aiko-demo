"""
Aiko ASR on Modal — faster-whisper large-v3-turbo
"""
import os
import tempfile
from pathlib import Path

import modal

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MINUTES = 60
MODEL_NAME = "large-v3-turbo"
COMPUTE_TYPE = "float16"
ASR_PORT = 8000
MODELS_DIR = Path("/models")

# ---------------------------------------------------------------------------
# Volume — persists downloaded model weights across deploys
# ---------------------------------------------------------------------------
volume = modal.Volume.from_name("aiko-asr-models", create_if_missing=True)

# ---------------------------------------------------------------------------
# Image — debian slim + CUDA cublas runtime + Python deps
# ---------------------------------------------------------------------------
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("libcublas12")
    .pip_install(
        "faster-whisper",
        "fastapi",
        "uvicorn[standard]",
        "python-multipart",
    )
)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = modal.App("aiko-asr", image=image)


# ---------------------------------------------------------------------------
# ASR Server class
# ---------------------------------------------------------------------------
@app.cls(
    gpu="T4",
    timeout=10 * MINUTES,
    scaledown_window=5 * MINUTES,
    min_containers=0,
    volumes={str(MODELS_DIR): volume},
    startup_timeout=10 * MINUTES,
)
class ASRServer:

    @modal.enter()
    def startup(self):
        """Load the Whisper model once — reused across all requests."""
        from faster_whisper import WhisperModel

        print(f"Loading faster-whisper {MODEL_NAME} ...")
        self.model = WhisperModel(
            MODEL_NAME,
            device="cuda",
            compute_type=COMPUTE_TYPE,
            download_root=str(MODELS_DIR),
        )
        print("Model ready.")
        volume.commit()  # persist downloaded weights

    @modal.web_endpoint(method="GET")
    def health(self):
        return {"status": "ok", "model": MODEL_NAME}

    @modal.web_endpoint(method="POST")
    async def transcribe(self, audio: "UploadFile"):  # type: ignore[name-defined]
        from fastapi import File, UploadFile
        from fastapi.responses import JSONResponse

        suffix = Path(audio.filename or "audio.wav").suffix or ".wav"

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(await audio.read())
            tmp_path = tmp.name

        try:
            segments, info = self.model.transcribe(
                tmp_path,
                beam_size=5,
                vad_filter=True,
                condition_on_previous_text=False,
            )
            text = " ".join(s.text.strip() for s in segments).strip()
            return JSONResponse({
                "text": text,
                "language": info.language,
                "language_probability": round(info.language_probability, 3),
            })
        finally:
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Local test entrypoint:  modal run asr.py [path/to/audio.wav]
# ---------------------------------------------------------------------------
@app.local_entrypoint()
def main():
    import sys
    import wave
    import struct
    import math
    import httpx

    test_audio = sys.argv[1] if len(sys.argv) > 1 else None

    # Generate a 1-second 440 Hz sine-wave WAV if no file provided
    if test_audio is None:
        test_audio = "/tmp/asr_test_tone.wav"
        with wave.open(test_audio, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            frames = [
                struct.pack("<h", int(32767 * math.sin(2 * math.pi * 440 * i / 16000)))
                for i in range(16000)
            ]
            wf.writeframes(b"".join(frames))
        print(f"No audio file given — generated test tone at {test_audio}")

    print(f"Testing with {test_audio} ...")

    server = ASRServer()
    url = server.transcribe.web_url

    with open(test_audio, "rb") as f:
        resp = httpx.post(
            url,
            files={"audio": (Path(test_audio).name, f, "audio/wav")},
            timeout=60,
        )

    resp.raise_for_status()
    print("✓", resp.json())