"""
Aiko ASR on Modal — faster-whisper large-v3-turbo
==================================================
Exposes a single POST /transcribe endpoint that accepts an audio file
and returns a JSON transcript.

Deploy:
  modal deploy backend/asr.py

Call from your Gradio Space:
  curl -X POST https://<workspace>--aiko-asr-server-serve.modal.run/transcribe \
       -F "audio=@recording.wav"
  → {"text": "Hello, how are you?", "language": "en"}
"""

import os
from pathlib import Path

import modal

MINUTES = 60
MODEL_NAME = "large-v3-turbo"
COMPUTE_TYPE = "float16"
ASR_PORT = 8000

# ---------------------------------------------------------------------------
# Shared volume — model weights cached after first download
# ---------------------------------------------------------------------------
volume = modal.Volume.from_name("aiko-asr-models", create_if_missing=True)
MODELS_DIR = Path("/models")

# ---------------------------------------------------------------------------
# Container image
# ---------------------------------------------------------------------------
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "faster-whisper",
        "fastapi",
        "uvicorn[standard]",
        "python-multipart",
    )
)

app = modal.App("aiko-asr", image=image)

# ---------------------------------------------------------------------------
# Model cache — lives inside the container process
# ---------------------------------------------------------------------------
_MODEL = None

def _get_model():
    global _MODEL
    if _MODEL is None:
        from faster_whisper import WhisperModel
        print(f"Loading faster-whisper {MODEL_NAME} ...")
        _MODEL = WhisperModel(
            MODEL_NAME,
            device="cuda",
            compute_type=COMPUTE_TYPE,
            download_root=str(MODELS_DIR),
        )
        print("Model ready.")
    return _MODEL


# ---------------------------------------------------------------------------
# Modal class
# ---------------------------------------------------------------------------
@app.cls(
    gpu="T4",
    timeout=5 * MINUTES,
    scaledown_window=5 * MINUTES,
    min_containers=0,
    volumes={str(MODELS_DIR): volume},
    secrets=[modal.Secret.from_name("huggingface")],  # add this
)
class ASRServer:

    @modal.enter()
    def startup(self):
        _get_model()
        volume.commit()

    @modal.web_server(port=ASR_PORT, startup_timeout=3 * MINUTES)
    def serve(self):
        # All imports inside — only runs inside the container
        import tempfile
        import uvicorn
        from fastapi import FastAPI, File, UploadFile
        from fastapi.responses import JSONResponse

        web_app = FastAPI()

        @web_app.get("/health")
        def health():
            return {"status": "ok"}

        @web_app.post("/transcribe")
        async def transcribe(audio: UploadFile = File(...)):
            suffix = Path(audio.filename or "audio.wav").suffix or ".wav"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(await audio.read())
                tmp_path = tmp.name
            try:
                model = _get_model()
                segments, info = model.transcribe(
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

        uvicorn.run(web_app, host="0.0.0.0", port=ASR_PORT)


# ---------------------------------------------------------------------------
# Smoke test:  modal run backend/asr.py
# ---------------------------------------------------------------------------
@app.local_entrypoint()
def main():
    import httpx, sys, wave, struct, math

    test_audio = sys.argv[1] if len(sys.argv) > 1 else None
    if test_audio is None:
        test_audio = "/tmp/asr_test_tone.wav"
        with wave.open(test_audio, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            frames = [struct.pack("<h", int(32767 * math.sin(2 * math.pi * 440 * i / 16000)))
                      for i in range(16000)]
            wf.writeframes(b"".join(frames))

    print(f"Testing with {test_audio} ...")
    with open(test_audio, "rb") as f:
        resp = httpx.post(
            f"http://localhost:{ASR_PORT}/transcribe",
            files={"audio": ("test.wav", f, "audio/wav")},
            timeout=30,
        )
    resp.raise_for_status()
    print("✓", resp.json())