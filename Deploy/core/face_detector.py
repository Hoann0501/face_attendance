"""
Face detection using InsightFace (buffalo_l).
"""

from __future__ import annotations

import numpy as np
from PIL import Image

from insightface.app import FaceAnalysis

from core.utils import pil_to_bgr, draw_thin_bbox


class FaceDetector:
    def __init__(self, det_size: tuple[int, int] = (640, 640)):
        print("[FaceDetector] Loading InsightFace buffalo_l ...")
        self.app = FaceAnalysis(
            name="buffalo_l",
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
        )
        self.app.prepare(ctx_id=0, det_size=det_size)
        print("[FaceDetector] Ready.")

    def detect_bgr(self, bgr: np.ndarray) -> list:
        """Return list of InsightFace Face objects."""
        return self.app.get(bgr)

    def detect_pil(self, pil_img: Image.Image) -> list:
        bgr = pil_to_bgr(pil_img)
        return self.detect_bgr(bgr)

    def get_largest_face(self, faces: list):
        if not faces:
            return None

        def area(f):
            x1, y1, x2, y2 = f.bbox
            return max(0, x2 - x1) * max(0, y2 - y1)

        return max(faces, key=area)

    def draw_faces(self, bgr: np.ndarray, faces: list) -> np.ndarray:
        import cv2
        out = bgr.copy()
        for i, face in enumerate(faces, 1):
            x1, y1, x2, y2 = face.bbox.astype(int)
            draw_thin_bbox(out, x1, y1, x2, y2, color=(0, 255, 0), thickness=2)
            cv2.putText(
                out,
                f"face_{i} {face.det_score:.2f}",
                (x1, max(20, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )
        return out
