"""
People management page.
"""

from __future__ import annotations

import sys
from pathlib import Path

DEPLOY_ROOT = Path(__file__).resolve().parent.parent.parent
if str(DEPLOY_ROOT) not in sys.path:
    sys.path.insert(0, str(DEPLOY_ROOT))

import requests
import pandas as pd
import streamlit as st

from backend.config import BACKEND_URL

API = BACKEND_URL


def _get(path, default=None):
    try:
        r = requests.get(f"{API}{path}", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return default


def _post(path, json=None, default=None):
    try:
        r = requests.post(f"{API}{path}", json=json, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return default


def _put(path, json=None):
    try:
        r = requests.put(f"{API}{path}", json=json, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def _patch(path, json=None):
    try:
        r = requests.patch(f"{API}{path}", json=json, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def _delete(path):
    try:
        r = requests.delete(f"{API}{path}", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def show():
    st.title("👥 Quản lý người")

    people = _get("/people", default=[])
    if people is None:
        people = []

    # ── Table ─────────────────────────────────────────────────────────────
    st.subheader(f"Danh sách – {len(people)} người")

    if people:
        df = pd.DataFrame(people)
        display_cols = ["person_id", "full_name", "student_code", "class_name", "status", "has_template", "created_at"]
        df_show = df[[c for c in display_cols if c in df.columns]].copy()

        def color_status(val):
            if val == "active":
                return "color: #4caf50; font-weight: bold"
            if val == "inactive":
                return "color: #f44336; font-weight: bold"
            return ""

        styled = df_show.style.map(color_status, subset=["status"])
        st.dataframe(styled, use_container_width=True, height=300)
    else:
        st.info("Chưa có người đăng ký.")

    st.markdown("---")
    col_add, col_edit = st.columns(2)

    # ── Add / Update person ───────────────────────────────────────────────
    with col_add:
        st.subheader("Thêm / cập nhật người")

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

        with st.form("add_person_form"):
            pid = st.text_input("person_id", value=_next_id())
            fname = st.text_input("Họ tên")
            scode = st.text_input("Mã sinh viên / nhân viên")
            cname = st.text_input("Lớp / phòng ban")
            status = st.selectbox("Trạng thái", ["active", "inactive"])
            submitted = st.form_submit_button("Lưu")

        if submitted:
            if not pid.strip():
                st.error("person_id không được rỗng")
            elif pid in existing_ids:
                result = _put(f"/people/{pid}", json={
                    "full_name": fname, "student_code": scode,
                    "class_name": cname, "status": status,
                })
                if result:
                    st.success(f"Đã cập nhật {pid}")
                    st.rerun()
            else:
                result = _post("/people", json={
                    "person_id": pid, "full_name": fname,
                    "student_code": scode, "class_name": cname, "status": status,
                })
                if result:
                    st.success(f"Đã thêm {pid}")
                    st.rerun()

    # ── Status / Delete ───────────────────────────────────────────────────
    with col_edit:
        st.subheader("Thay đổi trạng thái / xóa")

        if people:
            opts = [f"{p['person_id']} – {p.get('full_name','')}" for p in people]
            chosen = st.selectbox("Chọn người", opts)
            chosen_id = chosen.split(" – ")[0]

            ca, cb, cc = st.columns(3)

            with ca:
                if st.button("✅ Set active"):
                    result = _patch(f"/people/{chosen_id}/status", json={"status": "active"})
                    if result:
                        st.success(f"Active: {chosen_id}")
                        st.rerun()

            with cb:
                if st.button("🔒 Set inactive"):
                    result = _patch(f"/people/{chosen_id}/status", json={"status": "inactive"})
                    if result:
                        st.warning(f"Inactive: {chosen_id}")
                        st.rerun()

            with cc:
                confirm = st.checkbox("Xác nhận xóa", key="del_confirm")
                if st.button("🗑️ Xóa") and confirm:
                    result = _delete(f"/people/{chosen_id}")
                    if result:
                        st.success(f"Đã xóa {chosen_id}")
                        st.rerun()
        else:
            st.info("Không có người để chọn.")
