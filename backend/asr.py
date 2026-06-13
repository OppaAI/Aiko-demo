"""
Aiko ASR on Modal — faster-whisper large-v3-turbo
"""
import os
import tempfile
from pathlib import Path

import modal
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse

MINUTES = 60
MODEL_NAME = "large-v3-turbo"
COMPUTE_TYPE = "float16"
MODELS_DIR = Path("/models")

volume = modal.Volume.from_name("aiko-asr-models", create_if_missing=True)

image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.3.2-runtime-ubuntu22.04",
        add_python="3.12",
    )
    .pip_install(
        "faster-whisper",
        "fastapi",
        "uvicorn[standard]",
        "python-multipart",
    )
)

app = modal.App("aiko-asr", image=image)
web_app = FastAPI()


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
        from faster_whisper import WhisperModel
        print(f"Loading faster-whisper {MODEL_NAME} ...")
        self.model = WhisperModel(
            MODEL_NAME,
            device="cuda",
            compute_type=COMPUTE_TYPE,
            download_root=str(MODELS_DIR),
        )
        print("Model ready.")
        volume.commit()

    @modal.method()
    def _transcribe(self, audio_bytes: bytes, suffix: str) -> dict:
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            segments, info = self.model.transcribe(
                tmp_path,
                beam_size=5,
                vad_filter=True,
                condition_on_previous_text=False,
            )
            text = " ".join(s.text.strip() for s in segments).strip()
            return {
                "text": text,
                "language": info.language,
                "language_probability": round(info.language_probability, 3),
            }
        finally:
            os.unlink(tmp_path)


@web_app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_NAME}


@web_app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    suffix = Path(audio.filename or "audio.wav").suffix or ".wav"
    audio_bytes = await audio.read()
    server = ASRServer()
    result = server._transcribe.remote(audio_bytes, suffix)
    return JSONResponse(result)


@app.function()
@modal.asgi_app()
def fastapi_app():
    return web_app