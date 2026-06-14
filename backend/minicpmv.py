"""
MiniCPM-V 4.6 — Modal inference endpoint
Video is decoded manually with PyAV (bypasses transformers video pipeline entirely).
Frames are subsampled and resized before being passed as PIL images.
"""

import base64
import io
import os
import tempfile
from typing import Optional, List

import modal

TORCH_INDEX = "https://download.pytorch.org/whl/cu121"

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch==2.6.0",
        "torchvision==0.21.0",
        extra_index_url=TORCH_INDEX,
    )
    .pip_install(
        "transformers[torch]>=5.7.0",
        "av",
        "accelerate",
        "Pillow",
        "requests",
        "fastapi",
        "uvicorn",
    )
)

app = modal.App("minicpm-v-4-6", image=image)

MODEL_ID = "openbmb/MiniCPM-V-4.6"


def _decode_video_pyav(source: str | bytes, max_frames: int = 16, max_size: int = 448) -> List:
    """Decode video with PyAV, subsample to max_frames, resize to max_size."""
    import av
    from PIL import Image as PILImage

    if isinstance(source, (bytes, bytearray)):
        container = av.open(io.BytesIO(source))
    else:
        # URL or file path
        import requests
        if source.startswith("http"):
            resp = requests.get(source, timeout=30)
            resp.raise_for_status()
            container = av.open(io.BytesIO(resp.content))
        else:
            container = av.open(source)

    stream = container.streams.video[0]
    total = stream.frames or 0

    # Collect all frame pts first for uniform subsampling
    frames = []
    container.seek(0)
    for packet in container.demux(stream):
        for frame in packet.decode():
            frames.append(frame)

    container.close()

    if not frames:
        return []

    # Uniform subsample
    if len(frames) > max_frames:
        idxs = [int(i * len(frames) / max_frames) for i in range(max_frames)]
        frames = [frames[i] for i in idxs]

    # Convert to PIL and resize
    pil_frames = []
    for f in frames:
        img = f.to_image()  # PIL Image
        # Resize keeping aspect ratio
        w, h = img.size
        if max(w, h) > max_size:
            scale = max_size / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)), PILImage.LANCZOS)
        pil_frames.append(img)

    return pil_frames


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
            dtype=torch.bfloat16,
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
        max_num_frames: int = 16,
    ) -> str:
        import torch
        from PIL import Image

        content = []

        if image_url:
            content.append({"type": "image", "url": image_url})

        elif image_b64:
            img_bytes = base64.b64decode(image_b64)
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            content.append({"type": "image", "image": img})

        elif video_url or video_b64:
            # Decode video manually with PyAV — bypass transformers video pipeline
            if video_b64:
                source = base64.b64decode(video_b64)
            else:
                source = video_url

            frames = _decode_video_pyav(source, max_frames=max_num_frames)
            if not frames:
                return "Error: could not decode video."

            # Pass frames as multiple images
            for frame in frames:
                content.append({"type": "image", "image": frame})

        content.append({"type": "text", "text": prompt})
        messages = [{"role": "user", "content": content}]

        # All requests use image path (video frames passed as images)
        inputs = self.processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
            downsample_mode=downsample_mode,
            max_slice_nums=36,
        ).to(self.model.device)

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
        return self.processor.batch_decode(
            trimmed,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0]


# ---------------------------------------------------------------------------
# FastAPI
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
    max_num_frames: int = 16


class VisionResponse(BaseModel):
    text: str


@web_app.get("/health")
async def health():
    return {"status": "ok", "model": MODEL_ID}


@web_app.post("/vision", response_model=VisionResponse)
async def vision_endpoint(req: VisionRequest):
    n_inputs = sum([bool(req.image_url), bool(req.image_b64),
                    bool(req.video_url), bool(req.video_b64)])
    if n_inputs > 1:
        raise HTTPException(status_code=400,
            detail="Provide at most one of: image_url, image_b64, video_url, video_b64")

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


@app.local_entrypoint()
def main():
    model = VisionModel()

    print("=== Image test ===")
    result = model.infer.remote(
        prompt="What causes this phenomenon?",
        image_url="https://huggingface.co/datasets/openbmb/DemoCase/resolve/main/refract.png",
    )
    print(result)

    print("\n=== Video test (8 frames) ===")
    result = model.infer.remote(
        prompt="Describe what is happening in this video.",
        video_url="https://huggingface.co/datasets/openbmb/DemoCase/resolve/main/football.mp4",
        max_num_frames=8,
        max_new_tokens=512,
    )
    print(result)