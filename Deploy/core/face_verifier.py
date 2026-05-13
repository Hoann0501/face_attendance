"""
Face verification / recognition using InsightFace ArcFace embeddings.
"""

from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
from PIL import Image

from insightface.app import FaceAnalysis

from core.utils import pil_to_bgr, safe_crop_face_pil


class FaceVerifier:
    """
    Verifies identity using ArcFace embeddings from InsightFace.

    Templates are stored as a dict: { person_id: np.ndarray(512,) }
    The template vector is the mean-normalized embedding across enroll images.
    """

    def __init__(
        self,
        templates_path: str | Path,
        verify_threshold: float = 0.35,
        det_size: tuple[int, int] = (640, 640),
    ):
        self.templates_path = Path(templates_path)
        self.verify_threshold = verify_threshold

        print("[FaceVerifier] Loading InsightFace buffalo_l ...")
        self.face_app = FaceAnalysis(
            name="buffalo_l",
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
        )
        self.face_app.prepare(ctx_id=0, det_size=det_size)

        self.templates: dict[str, np.ndarray] = {}
        self.load_templates()
        print(f"[FaceVerifier] Ready. Templates={len(self.templates)}")

    # ------------------------------------------------------------------

    def load_templates(self):
        if self.templates_path.exists():
            with open(self.templates_path, "rb") as f:
                self.templates = pickle.load(f)
            print(f"[FaceVerifier] Loaded {len(self.templates)} templates from {self.templates_path}")
        else:
            self.templates = {}
            print(f"[FaceVerifier] No templates file at {self.templates_path}. Starting empty.")

    def save_templates(self):
        self.templates_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.templates_path, "wb") as f:
            pickle.dump(self.templates, f)

    def reload_templates(self):
        self.load_templates()

    # ------------------------------------------------------------------

    def extract_embedding_bgr(self, bgr: np.ndarray) -> tuple[np.ndarray | None, dict]:
        faces = self.face_app.get(bgr)

        if not faces:
            return None, {"ok": False, "reason": "no_face", "faces": []}

        face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        emb = face.embedding.astype(np.float32)
        emb = emb / (np.linalg.norm(emb) + 1e-9)

        return emb, {"ok": True, "face": face, "faces": faces}

    def extract_embedding_pil(self, pil_img: Image.Image) -> tuple[np.ndarray | None, dict]:
        bgr = pil_to_bgr(pil_img)
        return self.extract_embedding_bgr(bgr)

    def extract_embedding_bytes(self, image_bytes: bytes) -> tuple[np.ndarray | None, dict]:
        from core.utils import bytes_to_bgr
        bgr = bytes_to_bgr(image_bytes)
        if bgr is None:
            return None, {"ok": False, "reason": "decode_failed"}
        return self.extract_embedding_bgr(bgr)

    # ------------------------------------------------------------------

    def search_top_k(
        self, emb: np.ndarray, top_k: int = 5
    ) -> list[dict]:
        """Return sorted list of {person_id, similarity} descending."""
        if not self.templates:
            return []

        results = []
        for pid, template in self.templates.items():
            t = template.astype(np.float32)
            t = t / (np.linalg.norm(t) + 1e-9)
            sim = float(np.dot(emb, t))
            results.append({"person_id": pid, "similarity": sim})

        results.sort(key=lambda r: r["similarity"], reverse=True)
        return results[:top_k]

    def verify_person(
        self, person_id: str, emb: np.ndarray
    ) -> dict:
        """1-to-1 verification for a specific person_id."""
        if person_id not in self.templates:
            return {
                "is_verified": False,
                "similarity": 0.0,
                "threshold": self.verify_threshold,
                "reason": "person_not_in_templates",
            }

        template = self.templates[person_id].astype(np.float32)
        template = template / (np.linalg.norm(template) + 1e-9)
        sim = float(np.dot(emb, template))

        return {
            "is_verified": sim >= self.verify_threshold,
            "similarity": sim,
            "threshold": self.verify_threshold,
            "reason": "ok",
        }

    # ------------------------------------------------------------------

    def register_person(
        self,
        person_id: str,
        embeddings: list[np.ndarray],
    ) -> bool:
        """
        Create or update a template by averaging multiple embeddings.
        Returns True on success.
        """
        if not embeddings:
            return False

        embs = np.stack([e.astype(np.float32) for e in embeddings])
        mean_emb = embs.mean(axis=0)
        mean_emb = mean_emb / (np.linalg.norm(mean_emb) + 1e-9)

        self.templates[person_id] = mean_emb
        self.save_templates()
        return True

    def delete_person_template(self, person_id: str) -> bool:
        if person_id in self.templates:
            del self.templates[person_id]
            self.save_templates()
            return True
        return False

    def has_template(self, person_id: str) -> bool:
        return person_id in self.templates

    # ------------------------------------------------------------------

    def detect_all_faces_pil(self, pil_img: Image.Image) -> list:
        bgr = pil_to_bgr(pil_img)
        return self.face_app.get(bgr)
