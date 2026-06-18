"""
aiko_imagegen.py — FLUX.2 [klein] 9B image generation endpoint for Aiko
Modal app: oppa-ai-org--aiko-imagegen

Requires Modal secrets:
  - huggingface-secret (HF_TOKEN) — needed for gated 9B weights
"""

import io
import base64
import modal

# ---------------------------------------------------------------------------
# image — bake diffusers + torch into the container
# ---------------------------------------------------------------------------
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install(
        "torch==2.6.0",
        "torchvision",
        extra_index_url="https://download.pytorch.org/whl/cu124",
    )
    .pip_install(
        "git+https://github.com/huggingface/diffusers.git",
        "transformers",
        "accelerate",
        "huggingface_hub",
        "sentencepiece",
        "Pillow",
        "fastapi[standard]",
    )
    .env({
        # disable flash-attn-3 custom op registration that breaks on torch 2.6
        "DIFFUSERS_NO_FLASH_ATTN": "1",
    })
)

# ---------------------------------------------------------------------------
# volume — cache weights so cold starts don't re-download 18GB every time
# ---------------------------------------------------------------------------
volume = modal.Volume.from_name("aiko-imagegen-weights", create_if_missing=True)
WEIGHTS_DIR = "/weights"
MODEL_ID = "black-forest-labs/FLUX.2-klein-9B"

app = modal.App("aiko-imagegen", image=image)

# ---------------------------------------------------------------------------
# model class — loaded once per container, stays warm between requests
# ---------------------------------------------------------------------------
@app.cls(
    gpu="H100",
    secrets=[modal.Secret.from_name("huggingface-secret")],
    volumes={WEIGHTS_DIR: volume},
    timeout=120,
    scaledown_window=300,
)
@modal.concurrent(max_inputs=1)
class AikoImageGen:

    @modal.enter()
    def load(self):
        import os
        import torch
        from diffusers import Flux2KleinPipeline
        from huggingface_hub import snapshot_download

        hf_token = os.environ["HF_TOKEN"]
        local_path = f"{WEIGHTS_DIR}/flux2-klein-9b"

        # download once into the volume, reuse on warm starts
        if not os.path.exists(local_path):
            print("Downloading FLUX.2 klein 9B weights...")
            snapshot_download(
                MODEL_ID,
                local_dir=local_path,
                token=hf_token,
                ignore_patterns=["*.msgpack", "*.h5"],
            )
            volume.commit()
        else:
            print("Weights already cached, loading from volume...")

        self.pipe = Flux2KleinPipeline.from_pretrained(
            local_path,
            torch_dtype=torch.bfloat16,
        ).to("cuda")

        print("FLUX.2 klein 9B ready.")

    @modal.method()
    def generate(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        steps: int = 4,
        guidance_scale: float = 1.0,
        seed: int = -1,
    ) -> str:
        """Generate image, return base64-encoded PNG string."""
        import torch

        generator = None
        if seed >= 0:
            generator = torch.Generator(device="cuda").manual_seed(seed)

        result = self.pipe(
            prompt=prompt,
            width=width,
            height=height,
            num_inference_steps=steps,
            guidance_scale=guidance_scale,
            generator=generator,
        )

        image = result.images[0]

        # encode to base64 PNG for easy HTTP transport
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")


# ---------------------------------------------------------------------------
# FastAPI wrapper — matches the pattern of your existing Aiko endpoints
# ---------------------------------------------------------------------------
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

web_app = FastAPI()


class GenerateRequest(BaseModel):
    prompt: str
    width: int = 1024
    height: int = 1024
    steps: int = 4
    guidance_scale: float = 1.0
    seed: int = -1


class GenerateResponse(BaseModel):
    image_b64: str
    prompt: str


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("huggingface-secret")],
)
@modal.asgi_app()
def fastapi_app():
    model = AikoImageGen()

    @web_app.post("/generate", response_model=GenerateResponse)
    async def generate(req: GenerateRequest):
        if not req.prompt.strip():
            raise HTTPException(status_code=400, detail="prompt is required")

        image_b64 = await model.generate.remote.aio(
            prompt=req.prompt,
            width=req.width,
            height=req.height,
            steps=req.steps,
            guidance_scale=req.guidance_scale,
            seed=req.seed,
        )
        return GenerateResponse(image_b64=image_b64, prompt=req.prompt)

    @web_app.get("/health")
    async def health():
        return {"status": "ok", "model": "FLUX.2-klein-9B"}

    return web_app