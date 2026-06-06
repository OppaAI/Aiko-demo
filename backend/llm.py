import modal
import subprocess
import os

app = modal.App("aiko-llama")

# Volume to cache the model — only downloads once
volume = modal.Volume.from_name("aiko-models", create_if_missing=True)

image = (
    modal.Image.debian_slim()
    .apt_install("curl", "wget")
    .run_commands(
        # Install llama.cpp server binary
        "curl -L https://github.com/ggerganov/llama.cpp/releases/latest/download/llama-server-linux-x64 -o /usr/local/bin/llama-server",
        "chmod +x /usr/local/bin/llama-server"
    )
    .pip_install("huggingface_hub", "fastapi", "httpx")
)

MODEL_PATH = "/models/ministral-3b-q4.gguf"
HF_REPO    = "unsloth/Ministral-3-3B-Instruct-2512-GGUF"
HF_FILE    = "Ministral-3-3B-Instruct-2512-UD-Q4_K_XL.gguf"

@app.cls(
    image=image,
    gpu="T4",
    volumes={"/models": volume},
    timeout=300,
    container_idle_timeout=120,  # stays warm 2 min between requests
)
class AikoLLM:

    @modal.enter()
    def load_model(self):
        from huggingface_hub import hf_hub_download
        import threading

        # Download model if not cached
        if not os.path.exists(MODEL_PATH):
            print("Downloading model from HF...")
            path = hf_hub_download(
                repo_id=HF_REPO,
                filename=HF_FILE,
                local_dir="/models"
            )
            print(f"Model cached at {path}")
        else:
            print("Model already cached, skipping download")

        # Start llama.cpp server
        self._proc = subprocess.Popen([
            "/usr/local/bin/llama-server",
            "--model",     MODEL_PATH,
            "--port",      "8080",
            "--host",      "0.0.0.0",
            "--n-gpu-layers", "99",   # full GPU offload
            "--ctx-size",  "4096",
            "--threads",   "4",
        ])

        # Wait for server to be ready
        import time, httpx
        for _ in range(30):
            try:
                httpx.get("http://localhost:8080/health", timeout=2)
                print("llama.cpp server ready")
                break
            except:
                time.sleep(1)

    @modal.web_endpoint(method="POST", path="/v1/chat/completions")
    def chat(self, request: dict):
        import httpx
        resp = httpx.post(
            "http://localhost:8080/v1/chat/completions",
            json=request,
            timeout=120.0,
        )
        return resp.json()

    @modal.web_endpoint(method="GET", path="/health")
    def health(self):
        return {"status": "ok"}


if __name__ == "__main__":
    modal.runner.deploy_stub(app)