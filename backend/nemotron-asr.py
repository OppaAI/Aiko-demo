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
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("libsndfile1", "ffmpeg", "git")
    .pip_install("Cython", "packaging")
    .pip_install("torch", "torchaudio")
    .run_commands(
        'pip install "nemo_toolkit[asr] @ git+https://github.com/NVIDIA/NeMo.git@main"'
    )
    .run_commands(
        "git clone --depth 1 https://github.com/NVIDIA/NeMo.git /opt/NeMo"
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
        from huggingface_hub import hf_hub_download

        # Download/cache the .nemo checkpoint so the script can load it by path
        self.model = nemo_asr.models.ASRModel.from_pretrained(model_name=MODEL_ID)

        # Find the cached .nemo file path
        self.model_path = hf_hub_download(
            repo_id=MODEL_ID,
            filename="nemotron-3.5-asr-streaming-0.6b.nemo",
        )

    @modal.method()
    def transcribe(self, audio_bytes: bytes, language: str | None = None) -> str:
        import io
        import json
        import os
        import re
        import subprocess
        import tempfile

        import librosa
        import soundfile as sf

        audio, _ = librosa.load(io.BytesIO(audio_bytes), sr=16000, mono=True)

        lang = language if language and language != "None" else "auto"
        print(f"[transcribe] resolved lang={lang!r} (raw input={language!r})")

        with tempfile.TemporaryDirectory() as tmpdir:
            wav_path = os.path.join(tmpdir, "audio.wav")
            sf.write(wav_path, audio, 16000)

            duration = librosa.get_duration(y=audio, sr=16000)

            manifest_path = os.path.join(tmpdir, "manifest.jsonl")
            with open(manifest_path, "w") as f:
                f.write(json.dumps({
                    "audio_filepath": wav_path,
                    "duration": duration,
                    "text": "",
                }) + "\n")

            output_dir = os.path.join(tmpdir, "output")
            os.makedirs(output_dir, exist_ok=True)

            script = "/opt/NeMo/examples/asr/asr_cache_aware_streaming/speech_to_text_cache_aware_streaming_infer.py"
            cmd = [
                "python", script,
                f"model_path={self.model_path}",
                f"dataset_manifest={manifest_path}",
                "batch_size=1",
                f"target_lang={lang}",
                "att_context_size=[56,13]",
                "strip_lang_tags=true",
                f"output_path={output_dir}",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            print("[transcribe] stdout:", result.stdout[-3000:])
            print("[transcribe] stderr:", result.stderr[-3000:])

            if result.returncode != 0:
                raise RuntimeError(f"Inference script failed: {result.stderr[-2000:]}")

            # --- Primary: parse transcription directly from stdout ---
            match = re.search(
                r"Final streaming transcriptions:\s*\['(.+?)'\]",
                result.stdout,
            )
            if match:
                return match.group(1)

            # --- Fallback: look for output manifest file ---
            output_files = [
                f for f in os.listdir(output_dir)
                if f.endswith(".json") or f.endswith(".jsonl")
            ]
            if not output_files:
                raise RuntimeError(
                    f"No transcription found in stdout or output dir.\n"
                    f"stdout tail: {result.stdout[-500:]}"
                )

            out_path = os.path.join(output_dir, output_files[0])
            with open(out_path) as f:
                entry = json.loads(f.readline())

            return entry.get("pred_text", entry.get("text", ""))


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