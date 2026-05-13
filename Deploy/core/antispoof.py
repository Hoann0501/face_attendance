"""
Anti-spoofing / liveness detection service.
MobileNetV3-small trained on face crop + full frame.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image

from core.utils import expand_bbox


class AntiSpoofService:
    """
    Liveness detection using temporal voting over a sliding window.

    Each call to `update(face_crop_rgb, full_frame_rgb)` pushes a vote
    into the buffer and returns the current status string.

    Statuses: CHECKING | REAL_ATTENDANCE_OK | FAKE_OR_SUSPECT
    """

    def __init__(
        self,
        model_path: str | Path,
        device: str | None = None,
        real_threshold_face: float = 0.75,
        real_threshold_full: float = 0.55,
        window_size: int = 7,
        min_real_votes: int = 5,
    ):
        self.model_path = Path(model_path)
        self.real_threshold_face = real_threshold_face
        self.real_threshold_full = real_threshold_full
        self.window_size = window_size
        self.min_real_votes = min_real_votes

        self.device = torch.device(
            device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        )

        self._score_buffer: deque = deque(maxlen=window_size)
        self.last_face_real: float = 0.0
        self.last_full_real: float = 0.0

        self._load_model()

    def _load_model(self):
        if not self.model_path.exists():
            raise FileNotFoundError(f"Anti-spoof model not found: {self.model_path}")

        print(f"[AntiSpoofService] Loading model from {self.model_path} on {self.device}")
        checkpoint = torch.load(
            self.model_path, map_location=self.device, weights_only=False
        )

        classes = checkpoint.get("classes", ["fake", "real"])
        class_to_idx = checkpoint.get("class_to_idx", {"fake": 0, "real": 1})
        num_classes = len(classes)

        m = models.mobilenet_v3_small(weights=None)
        in_features = m.classifier[3].in_features
        m.classifier[3] = nn.Linear(in_features, num_classes)
        m.load_state_dict(checkpoint["model_state_dict"])
        m = m.to(self.device)
        m.eval()

        self.model = m
        self.fake_idx = class_to_idx.get("fake", 0)
        self.real_idx = class_to_idx.get("real", 1)

        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ])

        print(f"[AntiSpoofService] Loaded. Classes={classes}")

    # ------------------------------------------------------------------

    def predict_single(self, img_rgb: np.ndarray) -> tuple[float, float]:
        """Return (real_score, fake_score) for one image (H,W,3 uint8 RGB)."""
        pil = Image.fromarray(img_rgb).convert("RGB")
        x = self.transform(pil).unsqueeze(0).to(self.device)

        with torch.no_grad():
            logits = self.model(x)
            probs = torch.softmax(logits, dim=1)[0].detach().cpu().numpy()

        return float(probs[self.real_idx]), float(probs[self.fake_idx])

    def predict_face_crop(self, face_crop_rgb: np.ndarray) -> tuple[float, float]:
        return self.predict_single(face_crop_rgb)

    def predict_full_frame(self, full_frame_rgb: np.ndarray) -> tuple[float, float]:
        return self.predict_single(full_frame_rgb)

    # ------------------------------------------------------------------

    def update(
        self,
        face_crop_rgb: np.ndarray,
        full_frame_rgb: np.ndarray,
    ) -> str:
        """
        Push one frame into temporal buffer.
        Returns status: CHECKING | REAL_ATTENDANCE_OK | FAKE_OR_SUSPECT
        """
        face_real, _ = self.predict_face_crop(face_crop_rgb)
        full_real, _ = self.predict_full_frame(full_frame_rgb)

        self.last_face_real = face_real
        self.last_full_real = full_real

        frame_is_real = (
            face_real >= self.real_threshold_face
            and full_real >= self.real_threshold_full
        )

        self._score_buffer.append({
            "face_real": face_real,
            "full_real": full_real,
            "is_real": frame_is_real,
        })

        if len(self._score_buffer) < self.window_size:
            return "CHECKING"

        real_votes = sum(1 for item in self._score_buffer if item["is_real"])
        avg_face = float(np.mean([item["face_real"] for item in self._score_buffer]))
        avg_full = float(np.mean([item["full_real"] for item in self._score_buffer]))

        if (
            real_votes >= self.min_real_votes
            and avg_face >= self.real_threshold_face
            and avg_full >= self.real_threshold_full
        ):
            return "REAL_ATTENDANCE_OK"
        else:
            return "FAKE_OR_SUSPECT"

    def reset_buffer(self):
        self._score_buffer.clear()
        self.last_face_real = 0.0
        self.last_full_real = 0.0

    def get_buffer_stats(self) -> dict:
        if not self._score_buffer:
            return {
                "buffer_len": 0,
                "window_size": self.window_size,
                "real_votes": 0,
                "avg_face_real": 0.0,
                "avg_full_real": 0.0,
            }

        real_votes = sum(1 for item in self._score_buffer if item["is_real"])
        return {
            "buffer_len": len(self._score_buffer),
            "window_size": self.window_size,
            "real_votes": real_votes,
            "avg_face_real": float(np.mean([i["face_real"] for i in self._score_buffer])),
            "avg_full_real": float(np.mean([i["full_real"] for i in self._score_buffer])),
        }

    # ------------------------------------------------------------------
    # Static helper: extract face crop from BGR frame using Haar cascade
    # ------------------------------------------------------------------

    @staticmethod
    def get_haar_face_crop(
        frame_bgr: np.ndarray,
        face_cascade,
        margin: float = 0.35,
    ) -> tuple[np.ndarray | None, tuple | None]:
        """
        Detect largest face with Haar cascade (fast, no dep on InsightFace).
        Returns (face_crop_rgb, (x1,y1,x2,y2)) or (None, None).
        """
        import cv2
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
        )
        if len(faces) == 0:
            return None, None

        faces = sorted(faces, key=lambda b: b[2] * b[3], reverse=True)
        x, y, w, h = faces[0]
        img_h, img_w = frame_bgr.shape[:2]
        x1, y1, x2, y2 = expand_bbox(x, y, w, h, img_w, img_h, margin=margin)

        roi_bgr = frame_bgr[y1:y2, x1:x2]
        roi_rgb = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2RGB)
        return roi_rgb, (x1, y1, x2, y2)
