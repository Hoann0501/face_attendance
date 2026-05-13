"""
Utility helpers shared across core, backend, camera_app.
"""

from __future__ import annotations

import cv2
import numpy as np
from pathlib import Path
from PIL import Image


# ---------------------------------------------------------------------------
# Image conversion helpers
# ---------------------------------------------------------------------------

def bgr_to_rgb(bgr: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def rgb_to_bgr(rgb: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def pil_to_bgr(pil_img: Image.Image) -> np.ndarray:
    rgb = np.array(pil_img.convert("RGB"))
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def bgr_to_pil(bgr: np.ndarray) -> Image.Image:
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb)


def pil_to_rgb_array(pil_img: Image.Image) -> np.ndarray:
    return np.array(pil_img.convert("RGB"))


def bytes_to_bgr(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return bgr


def bytes_to_pil(image_bytes: bytes) -> Image.Image:
    bgr = bytes_to_bgr(image_bytes)
    if bgr is None:
        raise ValueError("Cannot decode image bytes")
    return bgr_to_pil(bgr)


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def draw_text_with_bg(
    img: np.ndarray,
    text: str,
    org: tuple[int, int],
    font_scale: float = 0.7,
    color: tuple[int, int, int] = (255, 255, 255),
    bg_color: tuple[int, int, int] = (0, 0, 0),
    thickness: int = 2,
) -> None:
    font = cv2.FONT_HERSHEY_SIMPLEX
    (tw, th), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    x, y = org

    cv2.rectangle(
        img,
        (x - 4, y - th - 8),
        (x + tw + 4, y + baseline + 4),
        bg_color,
        -1,
    )
    cv2.putText(img, text, (x, y), font, font_scale, color, thickness, cv2.LINE_AA)


def draw_thin_bbox(
    img: np.ndarray,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    color: tuple[int, int, int] = (0, 255, 0),
    thickness: int = 2,
) -> None:
    cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness)


# ---------------------------------------------------------------------------
# Face crop helpers
# ---------------------------------------------------------------------------

def expand_bbox(
    x: int, y: int, w: int, h: int,
    img_w: int, img_h: int,
    margin: float = 0.35,
) -> tuple[int, int, int, int]:
    mx = int(w * margin)
    my = int(h * margin)
    x1 = max(0, x - mx)
    y1 = max(0, y - my)
    x2 = min(img_w, x + w + mx)
    y2 = min(img_h, y + h + my)
    return x1, y1, x2, y2


def safe_crop_face_pil(
    pil_img: Image.Image,
    bbox: np.ndarray,
    margin: float = 0.15,
) -> Image.Image | None:
    img_w, img_h = pil_img.size
    x1, y1, x2, y2 = bbox.astype(int)
    bw, bh = x2 - x1, y2 - y1
    mx, my = int(bw * margin), int(bh * margin)
    x1c = max(0, x1 - mx)
    y1c = max(0, y1 - my)
    x2c = min(img_w, x2 + mx)
    y2c = min(img_h, y2 + my)
    if x2c <= x1c or y2c <= y1c:
        return None
    return pil_img.crop((x1c, y1c, x2c, y2c))


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
