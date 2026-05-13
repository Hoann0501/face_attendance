"""
Face search and verification page.
"""

from __future__ import annotations

import sys
from pathlib import Path

DEPLOY_ROOT = Path(__file__).resolve().parent.parent.parent
if str(DEPLOY_ROOT) not in sys.path:
    sys.path.insert(0, str(DEPLOY_ROOT))

import io
import requests
import pandas as pd
import streamlit as st
from PIL import Image

from backend.config import BACKEND_URL

API = BACKEND_URL


def show():
    st.title("🔍 Tìm kiếm / Xác minh khuôn mặt")

    tab_search, tab_verify = st.tabs(["🔎 Tìm kiếm (1-to-N)", "✅ Xác minh (1-to-1)"])

    # ── Search tab ─────────────────────────────────────────────────────────
    with tab_search:
        st.subheader("Tìm kiếm khuôn mặt – top-K người giống nhất")

        col_left, col_right = st.columns([1, 1])

        with col_left:
            query_file = st.file_uploader(
                "Upload ảnh query",
                type=["jpg", "jpeg", "png", "bmp", "webp"],
                key="search_file",
            )
            top_k = st.slider("Top K", 1, 10, 5)

        if query_file:
            pil = Image.open(query_file)
            col_left.image(pil, caption="Query image", width="stretch")
            query_file.seek(0)

            with st.spinner("Đang tìm kiếm ..."):
                try:
                    r = requests.post(
                        f"{API}/face/search?top_k={top_k}",
                        files={"image": (query_file.name, query_file.read(), query_file.type)},
                        timeout=30,
                    )
                    if r.status_code == 200:
                        data = r.json()
                        results = data.get("results", [])

                        with col_right:
                            st.markdown(f"**{data.get('num_faces', 0)} mặt detect được**")

                            if results:
                                df = pd.DataFrame(results)
                                display = ["person_id", "full_name", "student_code", "class_name", "status", "similarity"]
                                df_show = df[[c for c in display if c in df.columns]].copy()
                                df_show["similarity"] = df_show["similarity"].round(4)

                                best = results[0]
                                threshold = 0.35
                                if best["similarity"] >= threshold:
                                    st.success(
                                        f"✅ MATCH: **{best.get('full_name', best['person_id'])}** "
                                        f"| {best['person_id']} | sim={best['similarity']:.4f}"
                                    )
                                else:
                                    st.warning(
                                        f"⚠️ UNKNOWN. Best={best['person_id']} sim={best['similarity']:.4f}"
                                    )

                                st.dataframe(df_show, use_container_width=True)
                            else:
                                st.warning("Không tìm thấy kết quả.")
                    else:
                        st.error(f"Lỗi {r.status_code}: {r.text}")
                except Exception as e:
                    st.error(f"Lỗi: {e}")

    # ── Verify tab ─────────────────────────────────────────────────────────
    with tab_verify:
        st.subheader("Xác minh 1-to-1 với một người cụ thể")

        try:
            people = requests.get(f"{API}/people", timeout=5).json()
        except Exception:
            people = []

        if not people:
            st.warning("Chưa có người trong database.")
            return

        opts = [f"{p['person_id']} – {p.get('full_name','')}" for p in people]
        chosen = st.selectbox("Chọn người cần xác minh", opts, key="verify_person")
        chosen_id = chosen.split(" – ")[0]

        verify_file = st.file_uploader(
            "Upload ảnh query",
            type=["jpg", "jpeg", "png", "bmp", "webp"],
            key="verify_file",
        )

        if verify_file:
            col_v1, col_v2 = st.columns([1, 1])
            col_v1.image(Image.open(verify_file), caption="Query image", width="stretch")
            verify_file.seek(0)

            if st.button("🔐 Xác minh"):
                with st.spinner("Đang xác minh ..."):
                    try:
                        r = requests.post(
                            f"{API}/face/verify",
                            data={"person_id": chosen_id},
                            files={"image": (verify_file.name, verify_file.read(), verify_file.type)},
                            timeout=30,
                        )
                        if r.status_code == 200:
                            result = r.json()
                            with col_v2:
                                if result.get("is_verified"):
                                    st.success(
                                        f"✅ VERIFIED\n\n"
                                        f"similarity = **{result['similarity']:.4f}**\n\n"
                                        f"threshold = {result['threshold']}"
                                    )
                                else:
                                    st.error(
                                        f"❌ NOT VERIFIED\n\n"
                                        f"similarity = **{result['similarity']:.4f}**\n\n"
                                        f"threshold = {result['threshold']}"
                                    )
                        else:
                            st.error(f"Lỗi {r.status_code}: {r.text}")
                    except Exception as e:
                        st.error(f"Lỗi: {e}")
