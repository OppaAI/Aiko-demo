"""
Aiko ASR on Modal — faster-whisper large-v3-turbo
"""

import os
import subprocess
from pathlib import Path

import modal

MINUTES = 60
MODEL_NAME = "large-v3-turbo"
COMPUTE_TYPE = "float16"
ASR_PORT = 8000

volume = modal.Volume.from_name("aiko-asr-models", create_if_missing=True)
MODELS_DIR = Path("/models")

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


@app.cls(
    gpu="T4",
    timeout=10 * MINUTES,
    scaledown_window=5 * MINUTES,
    min_containers=0,
    volumes={str(MODELS_DIR): volume},
)
class ASRServer:

    @modal.enter()
    def startup(self):
        # Pre-load model — runs before web_server starts accepting traffic
        _get_model()
        volume.commit()

        # Start uvicorn as a non-blocking subprocess
        # Must be Popen (non-blocking) — uvicorn.run() would block and
        # prevent Modal from marking the container as ready
        self.proc = subprocess.Popen([
            "python", "-c", """
import os, tempfile
from pathlib import Path
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import uvicorn

MODEL_NAME = "large-v3-turbo"
COMPUTE_TYPE = "float16"
MODELS_DIR = "/models"
ASR_PORT = 8000

_MODEL = None
def _get_model():
    global _MODEL
    if _MODEL is None:
        from faster_whisper import WhisperModel
        _MODEL = WhisperModel(MODEL_NAME, device="cuda", compute_type=COMPUTE_TYPE, download_root=MODELS_DIR)
    return _MODEL

_get_model()  # pre-load

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
        segments, info = model.transcribe(tmp_path, beam_size=5, vad_filter=True, condition_on_previous_text=False)
        text = " ".join(s.text.strip() for s in segments).strip()
        return JSONResponse({"text": text, "language": info.language, "language_probability": round(info.language_probability, 3)})
    finally:
        os.unlink(tmp_path)

uvicorn.run(web_app, host="0.0.0.0", port=int(ASR_PORT))
"""
        ])

    @modal.exit()
    def teardown(self):
        self.proc.terminate()

    @modal.web_server(port=ASR_PORT, startup_timeout=10 * MINUTES)
    def serve(self):
        # Non-blocking — uvicorn is already running via Popen in startup()
        pass


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
            timeout=60,
        )
    resp.raise_for_status()
    print("✓", resp.json())