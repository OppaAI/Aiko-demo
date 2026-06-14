"""core/see.py — Vision inference via Modal MiniCPM-V endpoint.

Supports image and video files. Converts local files to base64 data-URLs
so they can be sent directly to the Modal endpoint without needing an
external URL.
"""

from __future__ import annotations

import base64
import mimetypes
import os
import re
from pathlib import Path

import requests

VISION_ENDPOINT = os.getenv(
    "VISION_ENDPOINT",
    "https://oppa-ai-org--minicpm-v-4-6-fastapi-app.modal.run/vision",
)

# Supported MIME prefixes
_IMAGE_RE = re.compile(r"^image/")
_VIDEO_RE = re.compile(r"^video/")

# Max frames to sample from a video (keep latency reasonable on HF Space)
DEFAULT_MAX_FRAMES = 32
DEFAULT_MAX_TOKENS = 512


def _file_to_data_url(path: str) -> tuple[str, str]:
    """Read a local file and return (data_url, mime_type)."""
    mime, _ = mimetypes.guess_type(path)
    if not mime:
        # Fallback guesses by extension
        ext = Path(path).suffix.lower()
        fallbacks = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png",  ".gif": "image/gif",
            ".webp": "image/webp",
            ".mp4": "video/mp4",  ".mov": "video/quicktime",
            ".avi": "video/avi",  ".webm": "video/webm",
            ".mkv": "video/x-matroska",
        }
        mime = fallbacks.get(ext, "application/octet-stream")

    data = Path(path).read_bytes()
    b64  = base64.b64encode(data).decode()
    return f"data:{mime};base64,{b64}", mime


def describe(
    file_path: str,
    prompt: str = "Describe what you see in detail.",
    max_frames: int = DEFAULT_MAX_FRAMES,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:
    """Send a local image or video file to the Modal vision endpoint.

    Args:
        file_path: Absolute or relative path to the uploaded file.
        prompt:    Instruction passed to MiniCPM-V.
        max_frames: How many video frames to sample (ignored for images).
        max_tokens: Max tokens for the model response.

    Returns:
        The model's description string, or an error message prefixed with
        "[vision error]" so callers can surface it gracefully.
    """
    if not file_path or not Path(file_path).exists():
        return "[vision error] File not found."

    data_url, mime = _file_to_data_url(file_path)
    is_video = bool(_VIDEO_RE.match(mime))

    payload: dict = {"prompt": prompt, "max_new_tokens": max_tokens}

    if is_video:
        payload["video_url"]     = data_url
        payload["max_num_frames"] = max_frames
    else:
        payload["image_url"] = data_url

    try:
        resp = requests.post(
            VISION_ENDPOINT,
            json=payload,
            timeout=120,       # vision inference can take a while
        )
        resp.raise_for_status()
        return resp.json().get("text", "[vision error] Empty response from model.")
    except requests.exceptions.Timeout:
        return "[vision error] Vision model timed out — try a shorter video or smaller image."
    except requests.exceptions.RequestException as exc:
        return f"[vision error] Request failed: {exc}"


def is_supported(file_path: str) -> bool:
    """Return True if the file looks like a supported image or video."""
    mime, _ = mimetypes.guess_type(file_path)
    if not mime:
        ext = Path(file_path).suffix.lower()
        return ext in {
            ".jpg", ".jpeg", ".png", ".gif", ".webp",
            ".mp4", ".mov", ".avi", ".webm", ".mkv",
        }
    return bool(_IMAGE_RE.match(mime) or _VIDEO_RE.match(mime))