"""
Modal deployment: NVIDIA Nemotron 3.5 ASR Streaming (0.6B) for Aiko-chan.

40 language-locales from a single checkpoint, incl. Japanese, Korean, English, etc.
600M params -> keeps Aiko under Tiny Titan's 4B cap.

Deploy:
    modal deploy modal_nemotron_asr.py

Call:
    POST https://<your-modal-app>--transcribe.modal.run
    multipart/form-data with field "audio" (wav file, 16kHz mono recommended)
    optional form field "language" (e.g. "en-US", "ja-JP") - omit for auto langid

Returns:
    {"text": "<transcription>"}
"""

import modal
import fastapi

app = modal.App("aiko-nemotron-asr")

image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("libsndfile1", "ffmpeg", "git")
    .pip_install("Cython", "packaging")
    .pip_install("torch", "torchaudio")
    .run_commands(
        'pip install "nemo_toolkit[asr] @ git+https://github.com/NVIDIA/NeMo.git@main"'
    )
    .pip_install("fastapi", "python-multipart", "soundfile", "librosa")
)

MODEL_ID = "nvidia/nemotron-3.5-asr-streaming-0.6b"

model_volume = modal.Volume.from_name("nemotron-asr-weights", create_if_missing=True)


@app.cls(
    image=image,
    gpu="T4",  # 600M model, T4 is plenty; bump if you batch
    volumes={"/root/.cache/huggingface": model_volume},
    scaledown_window=300,
    timeout=300,
)
class ASR:
    @modal.enter()
    def load_model(self):
        import nemo.collections.asr as nemo_asr

        self.model = nemo_asr.models.ASRModel.from_pretrained(model_name=MODEL_ID)
        self.model.eval()
        if hasattr(self.model, "cuda"):
            self.model = self.model.cuda()

    @modal.method()
    def transcribe(self, audio_bytes: bytes, language: str | None = None) -> str:
        import io
        import tempfile

        import librosa
        import soundfile as sf

        # Load and resample to 16kHz mono
        audio, _ = librosa.load(io.BytesIO(audio_bytes), sr=16000, mono=True)

        # NeMo's transcribe expects file paths
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            sf.write(f.name, audio, 16000)
            tmp_path = f.name

        # Guard against the literal string "None" (can happen via form
        # parsing) as well as Python None, and missing/empty values.
        lang = language if language and language != "None" else "auto"
        print(f"[transcribe] resolved lang={lang!r} (raw input={language!r})")

        transcripts = self.model.transcribe(paths2audio_files=[tmp_path], target_lang=lang)

        result = transcripts[0]
        # NeMo may return Hypothesis objects depending on version
        text = result.text if hasattr(result, "text") else result
        return text


@app.function(image=image, timeout=300)
@modal.fastapi_endpoint(method="POST")
async def transcribe(audio: fastapi.UploadFile = None, language: str | None = None):
    """
    HTTP endpoint wrapper.
    Expects multipart/form-data with an "audio" file field
    and optional "language" form field (e.g. "ja-JP", "en-US").
    Omit language for auto language-ID across the 40 supported locales.
    """
    asr = ASR()
    audio_bytes = await audio.read()
    text = await asr.transcribe.remote.aio(audio_bytes, language=language)
    return {"text": text}