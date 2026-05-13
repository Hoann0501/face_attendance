"""
Face registration page – upload 2-5 images to create/update a template.
"""

from __future__ import annotations

import sys
from pathlib import Path

DEPLOY_ROOT = Path(__file__).resolve().parent.parent.parent
if str(DEPLOY_ROOT) not in sys.path:
    sys.path.insert(0, str(DEPLOY_ROOT))

import requests
import streamlit as st
from PIL import Image
import io

from backend.config import BACKEND_URL

API = BACKEND_URL


def _get_people():
    try:
        r = requests.get(f"{API}/people", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return []


def show():
    st.title("📸 Đăng ký khuôn mặt")
    st.info(
        "Upload 2–5 ảnh rõ mặt của cùng một người. "
        "Backend sẽ tạo ArcFace embedding template và cập nhật database."
    )

    people = _get_people()
    existing_ids = [p["person_id"] for p in people] if people else []

    def _next_id():
        nums = []
        for pid in existing_ids:
            if pid.startswith("person_"):
                try:
                    nums.append(int(pid.split("_")[1]))
                except Exception:
                    pass
        return f"person_{(max(nums) + 1 if nums else 1):03d}"

    with st.form("register_face_form"):
        col1, col2 = st.columns(2)

        with col1:
            pid = st.text_input("person_id", value=_next_id())
            fname = st.text_input("Họ tên")

        with col2:
            scode = st.text_input("Mã sinh viên / nhân viên")
            cname = st.text_input("Lớp / phòng ban")

        uploaded_files = st.file_uploader(
            "Upload ảnh khuôn mặt (2–5 ảnh)",
            type=["jpg", "jpeg", "png", "bmp", "webp"],
            accept_multiple_files=True,
        )

        submitted = st.form_submit_button("🚀 Đăng ký")

    if submitted:
        if not pid.strip():
            st.error("person_id không được rỗng")
            return

        if not uploaded_files:
            st.error("Cần upload ít nhất 1 ảnh")
            return

        if len(uploaded_files) > 10:
            st.warning("Tối đa 10 ảnh. Chỉ lấy 10 ảnh đầu.")
            uploaded_files = uploaded_files[:10]

        # Preview images
        st.markdown("### Preview ảnh upload")
        preview_cols = st.columns(min(5, len(uploaded_files)))
        for i, f in enumerate(uploaded_files):
            with preview_cols[i % len(preview_cols)]:
                st.image(Image.open(f), caption=f.name, width="stretch")
            f.seek(0)

        # Build multipart request
        files = [("images", (f.name, f.read(), f.type)) for f in uploaded_files]
        data = {
            "person_id": pid.strip(),
            "full_name": fname,
            "student_code": scode,
            "class_name": cname,
        }

        with st.spinner("Đang tạo template ..."):
            try:
                r = requests.post(
                    f"{API}/face/register",
                    data=data,
                    files=files,
                    timeout=60,
                )

                if r.status_code == 200:
                    result = r.json()
                    st.success(f"✅ {result.get('message', 'Đăng ký thành công')}")

                    st.json({
                        "person_id": result.get("person_id"),
                        "images_processed": result.get("num_images_processed"),
                        "embeddings_created": result.get("num_embeddings_created"),
                        "template_updated": result.get("template_updated"),
                    })
                else:
                    st.error(f"Lỗi {r.status_code}: {r.text}")

            except Exception as e:
                st.error(f"Lỗi kết nối: {e}")

    # ── Existing people with templates ────────────────────────────────────
    st.markdown("---")
    st.subheader("Người đã có template")

    if people:
        has_tmpl = [p for p in people if p.get("has_template")]
        no_tmpl = [p for p in people if not p.get("has_template")]

        col_yes, col_no = st.columns(2)
        with col_yes:
            st.markdown(f"**✅ Có template ({len(has_tmpl)})**")
            for p in has_tmpl:
                st.write(f"• {p['person_id']} – {p.get('full_name', '')}")

        with col_no:
            st.markdown(f"**⚠️ Chưa có template ({len(no_tmpl)})**")
            for p in no_tmpl:
                st.write(f"• {p['person_id']} – {p.get('full_name', '')}")
    else:
        st.info("Chưa có người nào trong database.")
