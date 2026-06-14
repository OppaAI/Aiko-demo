"""
MiniCPM-V 4.6 — Modal inference endpoint
Supports: image (URL or base64), video (URL or base64), text-only

Endpoints:
  POST /vision   — main inference
  GET  /health   — liveness check

Request body (JSON):
  {
    "prompt": "What do you see?",
    "image_url": "https://...",          # optional — remote image
    "image_b64": "<base64 string>",      # optional — local image (png/jpg)
    "video_url": "https://...",          # optional — remote video
    "video_b64": "<base64 string>",      # optional — local video (mp4)
    "downsample_mode": "16x",            # "4x" for finer detail, "16x" for speed
    "max_new_tokens": 512,
    "max_num_frames": 128                # video only
  }

Only one of image_url / image_b64 / video_url / video_b64 should be set per request.

Note: uses PyAV (av) instead of torchvision to avoid torchvision.io.read_video removal.
"""

import base64
import io
import os
import tempfile
from typing import Optional

import modal

# ---------------------------------------------------------------------------
# Modal image — av instead of torchvision fixes the read_video AttributeError
# ---------------------------------------------------------------------------
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "transformers[torch]>=5.7.0",
        "av",           # PyAV — replaces torchvision for video decoding
        "accelerate",
        "Pillow",
        "fastapi",
        "uvicorn",
    )
)

app = modal.App("minicpm-v-4-6", image=image)

MODEL_ID = "openbmb/MiniCPM-V-4.6"


@app.cls(
    gpu="T4",
    scaledown_window=300,
    volumes={},
)
class VisionModel:

    @modal.enter()
    def load(self):
        from transformers import AutoModelForImageTextToText, AutoProcessor
        import torch

        print(f"[vision] Loading {MODEL_ID} ...")
        self.processor = AutoProcessor.from_pretrained(MODEL_ID)
        self.model = AutoModelForImageTextToText.from_pretrained(
            MODEL_ID,
            torch_dtype=torch.bfloat16,
            device_map="auto",
        )
        self.model.eval()
        print("[vision] Model ready.")

    @modal.method()
    def infer(
        self,
        prompt: str,
        image_url: Optional[str] = None,
        image_b64: Optional[str] = None,
        video_url: Optional[str] = None,
        video_b64: Optional[str] = None,
        downsample_mode: str = "16x",
        max_new_tokens: int = 512,
        max_num_frames: int = 128,
    ) -> str:
        import torch
        from PIL import Image

        # ---- Build content list ----------------------------------------
        content = []
        tmp_path = None

        if image_url:
            content.append({"type": "image", "url": image_url})

        elif image_b64:
            img_bytes = base64.b64decode(image_b64)
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            content.append({"type": "image", "image": img})

        elif video_url:
            content.append({"type": "video", "url": video_url})

        elif video_b64:
            video_bytes = base64.b64decode(video_b64)
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                f.write(video_bytes)
                tmp_path = f.name
            content.append({"type": "video", "url": f"file://{tmp_path}"})

        content.append({"type": "text", "text": prompt})
        messages = [{"role": "user", "content": content}]

        # ---- Tokenise — kwargs directly in apply_chat_template (official API) --
        is_video = bool(video_url or video_b64)

        if is_video:
            inputs = self.processor.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                return_dict=True,
                return_tensors="pt",
                downsample_mode=downsample_mode,
                max_num_frames=max_num_frames,
                stack_frames=1,
                max_slice_nums=1,
                use_image_id=False,
            ).to(self.model.device)
        else:
            inputs = self.processor.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                return_dict=True,
                return_tensors="pt",
                downsample_mode=downsample_mode,
                max_slice_nums=36,
            ).to(self.model.device)

        # ---- Generate --------------------------------------------------
        with torch.inference_mode():
            generated_ids = self.model.generate(
                **inputs,
                downsample_mode=downsample_mode,
                max_new_tokens=max_new_tokens,
            )

        trimmed = [
            out[len(inp):]
            for inp, out in zip(inputs.input_ids, generated_ids)
        ]
        text = self.processor.batch_decode(
            trimmed,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0]

        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

        return text


# ---------------------------------------------------------------------------
# FastAPI web endpoint
# ---------------------------------------------------------------------------
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

web_app = FastAPI(title="MiniCPM-V 4.6 Vision API")


class VisionRequest(BaseModel):
    prompt: str
    image_url: Optional[str] = None
    image_b64: Optional[str] = None
    video_url: Optional[str] = None
    video_b64: Optional[str] = None
    downsample_mode: str = "16x"
    max_new_tokens: int = 512
    max_num_frames: int = 128


class VisionResponse(BaseModel):
    text: str


@web_app.get("/health")
async def health():
    return {"status": "ok", "model": MODEL_ID}


@web_app.post("/vision", response_model=VisionResponse)
async def vision_endpoint(req: VisionRequest):
    n_inputs = sum([
        bool(req.image_url),
        bool(req.image_b64),
        bool(req.video_url),
        bool(req.video_b64),
    ])
    if n_inputs > 1:
        raise HTTPException(
            status_code=400,
            detail="Provide at most one of: image_url, image_b64, video_url, video_b64",
        )

    model = VisionModel()
    result = model.infer.remote(
        prompt=req.prompt,
        image_url=req.image_url,
        image_b64=req.image_b64,
        video_url=req.video_url,
        video_b64=req.video_b64,
        downsample_mode=req.downsample_mode,
        max_new_tokens=req.max_new_tokens,
        max_num_frames=req.max_num_frames,
    )
    return VisionResponse(text=result)


@app.function()
@modal.asgi_app()
def fastapi_app():
    return web_app


# ---------------------------------------------------------------------------
# Local test — modal run minicpmv.py
# ---------------------------------------------------------------------------
@app.local_entrypoint()
def main():
    model = VisionModel()

    print("=== Image test (URL) ===")
    result = model.infer.remote(
        prompt="What causes this phenomenon?",
        image_url="https://huggingface.co/datasets/openbmb/DemoCase/resolve/main/refract.png",
    )
    print(result)

    print("\n=== Video test (URL) ===")
    result = model.infer.remote(
        prompt="Describe this video in detail. Follow the timeline and focus on on-screen text, interface changes, main actions, and scene changes.",
        video_url="https://huggingface.co/datasets/openbmb/DemoCase/resolve/main/football.mp4",
        max_new_tokens=2048,
        max_num_frames=128,
    )
    print(result)