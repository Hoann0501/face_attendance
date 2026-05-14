"""
Face service: registration, search, verification, analysis.
Wraps core FaceVerifier and FaceAttributeAnalyzer.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

import time as _time
from backend.config import (
    TEMPLATES_PATH,
    VERIFY_THRESHOLD,
    ATTRIBUTE_MODEL_PATH,
    ENROLL_IMAGES_DIR,
)
from core.face_verifier import FaceVerifier
from core.face_attribute import FaceAttributeAnalyzer
from core.utils import safe_crop_face_pil, bytes_to_pil, pil_to_bgr


# ---------------------------------------------------------------------------
# Singleton instances (loaded once per process)
# ---------------------------------------------------------------------------

_face_verifier: FaceVerifier | None = None
_face_attr: FaceAttributeAnalyzer | None = None


def get_face_verifier() -> FaceVerifier:
    global _face_verifier
    if _face_verifier is None:
        _face_verifier = FaceVerifier(
            templates_path=TEMPLATES_PATH,
            verify_threshold=VERIFY_THRESHOLD,
        )
    return _face_verifier


def get_face_attribute_analyzer() -> FaceAttributeAnalyzer:
    global _face_attr
    if _face_attr is None:
        _face_attr = FaceAttributeAnalyzer(model_path=ATTRIBUTE_MODEL_PATH)
    return _face_attr


# ---------------------------------------------------------------------------

def register_face(
    person_id: str,
    image_bytes_list: list[bytes],
    full_name: str = "",
    student_code: str = "",
    class_name: str = "",
) -> dict:
    verifier = get_face_verifier()
    embeddings = []

    # Save enroll images to data/enroll_images/{person_id}/
    person_enroll_dir = ENROLL_IMAGES_DIR / person_id
    person_enroll_dir.mkdir(parents=True, exist_ok=True)

    for idx, img_bytes in enumerate(image_bytes_list, 1):
        try:
            pil_img = bytes_to_pil(img_bytes)
        except Exception:
            continue

        emb, info = verifier.extract_embedding_pil(pil_img)
        if info["ok"] and emb is not None:
            embeddings.append(emb)
            # Save the image file
            try:
                ts       = _time.strftime("%Y%m%d_%H%M%S")
                img_path = person_enroll_dir / f"enroll_{idx:02d}_{ts}.jpg"
                pil_img.save(str(img_path), "JPEG", quality=92)
            except Exception as e:
                print(f"[FaceService] Warning: could not save enroll image: {e}")

    if not embeddings:
        return {
            "ok": False,
            "num_images_processed": len(image_bytes_list),
            "num_embeddings_created": 0,
            "template_updated": False,
            "person_upserted": False,
            "message": "Không tạo được embedding nào. Kiểm tra lại ảnh.",
        }

    template_updated = verifier.register_person(person_id, embeddings)

    from backend.services.person_service import upsert_person
    upsert_person(
        person_id=person_id,
        full_name=full_name,
        student_code=student_code,
        class_name=class_name,
        status="active",
    )

    return {
        "ok": True,
        "num_images_processed": len(image_bytes_list),
        "num_embeddings_created": len(embeddings),
        "template_updated": template_updated,
        "person_upserted": True,
        "message": f"Đã đăng ký {person_id} với {len(embeddings)} ảnh.",
    }


def search_face(image_bytes: bytes, top_k: int = 5) -> dict:
    verifier = get_face_verifier()

    try:
        pil_img = bytes_to_pil(image_bytes)
    except Exception as e:
        return {"ok": False, "message": str(e), "results": []}

    bgr = pil_to_bgr(pil_img)
    faces = verifier.face_app.get(bgr)

    if not faces:
        return {"ok": False, "message": "Không detect được khuôn mặt", "num_faces": 0, "results": []}

    largest = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    emb = largest.embedding.astype(np.float32)
    emb = emb / (np.linalg.norm(emb) + 1e-9)

    top_results = verifier.search_top_k(emb, top_k=top_k)

    from backend.services.person_service import get_person
    enriched = []
    for r in top_results:
        p = get_person(r["person_id"]) or {}
        enriched.append({
            "person_id": r["person_id"],
            "full_name": p.get("full_name", ""),
            "student_code": p.get("student_code", ""),
            "class_name": p.get("class_name", ""),
            "status": p.get("status", ""),
            "similarity": r["similarity"],
        })

    return {"ok": True, "num_faces": len(faces), "results": enriched}


def verify_face(person_id: str, image_bytes: bytes) -> dict:
    verifier = get_face_verifier()

    try:
        pil_img = bytes_to_pil(image_bytes)
    except Exception as e:
        return {"ok": False, "message": str(e)}

    emb, info = verifier.extract_embedding_pil(pil_img)
    if not info["ok"]:
        return {"ok": False, "message": "Không detect được khuôn mặt", "is_verified": False}

    result = verifier.verify_person(person_id, emb)
    return {"ok": True, **result}


def analyze_faces(image_bytes: bytes) -> dict:
    verifier = get_face_verifier()
    attr = get_face_attribute_analyzer()

    try:
        pil_img = bytes_to_pil(image_bytes)
    except Exception as e:
        return {"ok": False, "message": str(e), "num_faces": 0, "faces": []}

    bgr = pil_to_bgr(pil_img)
    faces = verifier.face_app.get(bgr)

    results = []
    for i, face in enumerate(faces, 1):
        x1, y1, x2, y2 = face.bbox.astype(int)

        row: dict = {
            "face_id": i,
            "det_score": round(float(face.det_score), 4),
            "bbox": [round(float(v), 1) for v in face.bbox],
        }

        if hasattr(face, "kps") and face.kps is not None:
            row["landmarks"] = face.kps.astype(float).round(2).tolist()

        if hasattr(face, "embedding") and face.embedding is not None:
            row["embedding_dim"] = int(len(face.embedding))

        face_crop = safe_crop_face_pil(pil_img, face.bbox, margin=0.15)
        if face_crop is not None and attr.is_ready():
            attr_result = attr.predict_pil(face_crop)
            row.update({
                "gender": attr_result.get("gender"),
                "gender_conf": round(attr_result.get("gender_conf", 0.0), 4),
                "age": round(attr_result.get("age", 0.0), 1) if attr_result.get("age") is not None else None,
                "age_group": attr_result.get("age_group"),
                "age_group_conf": round(attr_result.get("age_group_conf", 0.0), 4),
            })

        results.append(row)

    return {"ok": True, "num_faces": len(faces), "faces": results}


def reload_templates():
    """Call after registering new person to refresh in-memory templates."""
    verifier = get_face_verifier()
    verifier.reload_templates()
