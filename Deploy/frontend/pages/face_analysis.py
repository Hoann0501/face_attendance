"""
Face image analysis page – detect, bbox, gender, age.
"""

from __future__ import annotations

import sys
from pathlib import Path

DEPLOY_ROOT = Path(__file__).resolve().parent.parent.parent
if str(DEPLOY_ROOT) not in sys.path:
    sys.path.insert(0, str(DEPLOY_ROOT))

import cv2
import requests
import numpy as np
import streamlit as st
from PIL import Image

from backend.config import BACKEND_URL

API = BACKEND_URL


def _draw_faces(pil_img: Image.Image, faces: list) -> Image.Image:
    bgr = cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)

    for face in faces:
        bbox = face.get("bbox", [])
        if len(bbox) == 4:
            x1, y1, x2, y2 = [int(v) for v in bbox]
            cv2.rectangle(bgr, (x1, y1), (x2, y2), (0, 220, 0), 2)

            # Label: face id + score
            label = f"#{face['face_id']}  {face.get('det_score', 0):.2f}"
            cv2.putText(bgr, label, (x1, max(18, y1 - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 0), 2)

            # Gender + age below bbox
            gender = face.get("gender") or ""
            age    = face.get("age")
            ag     = face.get("age_group") or ""
            if gender or ag:
                age_str = f"{age:.0f} tuoi" if age is not None else ag
                info = f"{gender}  {age_str}"
                cv2.putText(bgr, info, (x1, y2 + 18),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 220, 0), 2)

    return Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))


def show():
    st.title("🧬 Phân tích ảnh khuôn mặt")

    analysis_file = st.file_uploader(
        "Upload ảnh để phân tích",
        type=["jpg", "jpeg", "png", "bmp", "webp"],
        key="analysis_file",
    )

    if not analysis_file:
        return

    pil_img = Image.open(analysis_file)
    analysis_file.seek(0)

    with st.spinner("Đang phân tích ..."):
        try:
            r = requests.post(
                f"{API}/face/analyze",
                files={"image": (analysis_file.name, analysis_file.read(), analysis_file.type)},
                timeout=60,
            )
        except Exception as e:
            st.error(f"Lỗi kết nối: {e}")
            return

    if r.status_code != 200:
        st.error(f"Lỗi {r.status_code}: {r.text}")
        return

    data  = r.json()
    faces = data.get("faces", [])
    num   = data.get("num_faces", 0)

    if not faces:
        col_img, _ = st.columns([1, 1])
        col_img.image(pil_img, caption="Ảnh gốc", width="stretch")
        st.warning("Không detect được khuôn mặt.")
        return

    st.markdown(f"**Detect được {num} khuôn mặt**")

    col_img, col_data = st.columns([1, 1])

    with col_img:
        annotated = _draw_faces(pil_img, faces)
        st.image(annotated, caption="Annotated", width="stretch")

    with col_data:
        for face in faces:
            bbox = face.get("bbox", [])
            bbox_str = ""
            if len(bbox) == 4:
                bbox_str = f"({bbox[0]:.0f}, {bbox[1]:.0f}) → ({bbox[2]:.0f}, {bbox[3]:.0f})"

            gender      = face.get("gender") or "–"
            gender_conf = face.get("gender_conf")
            age         = face.get("age")
            age_group   = face.get("age_group") or "–"
            age_gc      = face.get("age_group_conf")
            emb_dim     = face.get("embedding_dim")

            # Card per face
            with st.container(border=True):
                st.markdown(f"#### Khuôn mặt #{face['face_id']}")

                r1, r2, r3 = st.columns(3)
                r1.metric("Det score",   f"{face.get('det_score', 0):.3f}")
                r2.metric("Giới tính",   f"{gender}  {gender_conf:.0%}" if gender_conf else gender)
                r3.metric("Tuổi",        f"{age:.0f}" if age is not None else "–")

                r4, r5, r6 = st.columns(3)
                r4.metric("Nhóm tuổi",  f"{age_group}  {age_gc:.0%}" if age_gc else age_group)
                r5.metric("Emb dim",    str(emb_dim) if emb_dim else "–")
                r6.metric("BBox",       bbox_str)

    with st.expander("JSON raw"):
        st.json(faces)
