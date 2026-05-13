"""
Face attribute analysis: gender, age_group, approximate age.
MobileNetV3-small multi-task model trained on UTKFace.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image

from core.utils import safe_crop_face_pil


class _FaceAttributeModel(nn.Module):
    def __init__(self, num_age_groups: int = 5, num_genders: int = 2, has_age_regression: bool = True):
        super().__init__()
        base = models.mobilenet_v3_small(weights=None)
        self.features = base.features
        self.avgpool = base.avgpool
        in_features = base.classifier[0].in_features

        self.shared = nn.Sequential(
            nn.Linear(in_features, 512),
            nn.Hardswish(),
            nn.Dropout(p=0.2),
        )

        self.gender_head = nn.Linear(512, num_genders)
        self.age_group_head = nn.Linear(512, num_age_groups)
        self.has_age_regression = has_age_regression

        if has_age_regression:
            self.age_head = nn.Linear(512, 1)

    def forward(self, x: torch.Tensor) -> dict:
        x = self.features(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.shared(x)

        out: dict = {
            "gender": self.gender_head(x),
            "age_group": self.age_group_head(x),
        }

        if self.has_age_regression:
            out["age"] = self.age_head(x).squeeze(1)

        return out


class FaceAttributeAnalyzer:
    """
    Predict gender, age_group, and approximate age for a face image.
    """

    def __init__(self, model_path: str | Path, device: str | None = None):
        self.model_path = Path(model_path)

        self.device = torch.device(
            device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        )

        self.model: _FaceAttributeModel | None = None
        self.transform: transforms.Compose | None = None
        self.gender_to_label: dict[int, str] = {}
        self.idx_to_age_group: dict[int, str] = {}
        self.has_age_regression: bool = True

        self._load_model()

    def _load_model(self):
        if not self.model_path.exists():
            print(f"[FaceAttributeAnalyzer] Model not found: {self.model_path}. Analyzer disabled.")
            return

        print(f"[FaceAttributeAnalyzer] Loading from {self.model_path} on {self.device}")
        checkpoint = torch.load(
            self.model_path, map_location=self.device, weights_only=False
        )

        age_group_order = checkpoint.get(
            "age_group_order", ["child", "teen", "adult", "middle_age", "senior"]
        )
        gender_to_label_raw = checkpoint.get("gender_to_label", {0: "male", 1: "female"})
        idx_to_age_group_raw = checkpoint.get(
            "idx_to_age_group", {i: g for i, g in enumerate(age_group_order)}
        )
        self.has_age_regression = checkpoint.get("has_age_regression", True)

        self.gender_to_label = {int(k): v for k, v in gender_to_label_raw.items()}
        self.idx_to_age_group = {int(k): v for k, v in idx_to_age_group_raw.items()}

        m = _FaceAttributeModel(
            num_age_groups=len(age_group_order),
            num_genders=len(self.gender_to_label),
            has_age_regression=self.has_age_regression,
        ).to(self.device)

        m.load_state_dict(checkpoint["model_state_dict"])
        m.eval()

        self.model = m
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ])

        print(
            f"[FaceAttributeAnalyzer] Loaded. "
            f"genders={list(self.gender_to_label.values())}, "
            f"age_groups={list(self.idx_to_age_group.values())}, "
            f"has_age_regression={self.has_age_regression}"
        )

    def is_ready(self) -> bool:
        return self.model is not None

    def predict_pil(self, face_pil: Image.Image) -> dict:
        """
        Predict attributes for a single face PIL image.
        Returns dict with: gender, gender_conf, age_group, age_group_conf, age (if available)
        """
        if not self.is_ready():
            return {
                "gender": None,
                "gender_conf": None,
                "age_group": None,
                "age_group_conf": None,
                "age": None,
            }

        x = self.transform(face_pil.convert("RGB")).unsqueeze(0).to(self.device)

        with torch.no_grad():
            outputs = self.model(x)

            gender_prob = torch.softmax(outputs["gender"], dim=1)[0].cpu().numpy()
            age_prob = torch.softmax(outputs["age_group"], dim=1)[0].cpu().numpy()

        gender_idx = int(np.argmax(gender_prob))
        age_idx = int(np.argmax(age_prob))

        result = {
            "gender": self.gender_to_label.get(gender_idx, str(gender_idx)),
            "gender_conf": float(gender_prob[gender_idx]),
            "age_group": self.idx_to_age_group.get(age_idx, str(age_idx)),
            "age_group_conf": float(age_prob[age_idx]),
            "age": None,
        }

        if self.has_age_regression and "age" in outputs:
            raw = float(outputs["age"][0].cpu().item())
            result["age"] = round(max(0.0, min(100.0, raw * 100.0)), 1)

        return result

    def predict_rgb(self, face_rgb: np.ndarray) -> dict:
        pil = Image.fromarray(face_rgb).convert("RGB")
        return self.predict_pil(pil)
