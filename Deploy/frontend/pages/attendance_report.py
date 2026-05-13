"""
Attendance report page – view, filter, export.
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
from datetime import date

from backend.config import BACKEND_URL

API = BACKEND_URL


def _api_report(date_str: str) -> dict:
    try:
        r = requests.get(f"{API}/attendance/report?date={date_str}", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return {}


def _color_status(val: str) -> str:
    if val in ("PRESENT", "CHECK_IN"):
        return "background-color: #1a5c1a; color: white; font-weight: bold"
    if val == "ABSENT":
        return "background-color: #8b0000; color: white; font-weight: bold"
    if val in ("CHECKED_OUT", "CHECK_OUT"):
        return "background-color: #1a3fa0; color: white; font-weight: bold"
    return ""


def show():
    st.title("📋 Báo cáo điểm danh")

    # Auto-refresh
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=5000, key="report_refresh")
    except ImportError:
        pass

    col_date, col_refresh = st.columns([2, 1])
    with col_date:
        selected_date = st.date_input("Chọn ngày", value=date.today())
    with col_refresh:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Làm mới"):
            st.rerun()

    date_str = selected_date.isoformat()
    report = _api_report(date_str)

    if not report:
        st.warning("Không lấy được dữ liệu. Kiểm tra backend.")
        return

    # ── Summary metrics ───────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng active", report.get("total_active", 0))
    c2.metric("Check-in (PRESENT)", report.get("present_count", 0))
    c3.metric("Check-out (CHECKED_OUT)", report.get("checked_out_count", 0))
    c4.metric("Vắng (ABSENT)", report.get("absent_count", 0))

    # ── Build full table ──────────────────────────────────────────────────
    all_rows = []

    for r in report.get("present", []):
        all_rows.append({
            "person_id": r.get("person_id", ""),
            "Họ tên": r.get("full_name", ""),
            "Mã SV": r.get("student_code", ""),
            "Lớp": r.get("class_name", ""),
            "Trạng thái": "PRESENT",
            "Check-in": (r.get("check_in_time") or "")[:19],
            "Check-out": "",
            "Similarity": round(float(r.get("check_in_similarity") or 0), 4),
            "Liveness": r.get("check_in_liveness_status", ""),
        })

    for r in report.get("checked_out", []):
        all_rows.append({
            "person_id": r.get("person_id", ""),
            "Họ tên": r.get("full_name", ""),
            "Mã SV": r.get("student_code", ""),
            "Lớp": r.get("class_name", ""),
            "Trạng thái": "CHECKED_OUT",
            "Check-in": (r.get("check_in_time") or "")[:19],
            "Check-out": (r.get("check_out_time") or "")[:19],
            "Similarity": round(float(r.get("check_in_similarity") or 0), 4),
            "Liveness": r.get("check_in_liveness_status", ""),
        })

    for r in report.get("absent", []):
        all_rows.append({
            "person_id": r.get("person_id", ""),
            "Họ tên": r.get("full_name", ""),
            "Mã SV": r.get("student_code", ""),
            "Lớp": r.get("class_name", ""),
            "Trạng thái": "ABSENT",
            "Check-in": "",
            "Check-out": "",
            "Similarity": 0.0,
            "Liveness": "",
        })

    if not all_rows:
        st.info("Không có dữ liệu cho ngày này.")
        return

    df = pd.DataFrame(all_rows)

    # ── Filters ───────────────────────────────────────────────────────────
    st.markdown("---")
    col_f1, col_f2, col_f3 = st.columns(3)

    with col_f1:
        status_filter = st.multiselect(
            "Lọc trạng thái",
            ["PRESENT", "ABSENT", "CHECKED_OUT"],
            default=["PRESENT", "ABSENT", "CHECKED_OUT"],
        )

    with col_f2:
        search_name = st.text_input("Tìm theo tên / mã SV")

    with col_f3:
        class_list = sorted(df["Lớp"].dropna().unique().tolist())
        class_filter = st.multiselect("Lọc lớp", class_list, default=class_list)

    df_filtered = df[df["Trạng thái"].isin(status_filter)]

    if search_name.strip():
        q = search_name.strip().lower()
        df_filtered = df_filtered[
            df_filtered["Họ tên"].str.lower().str.contains(q, na=False) |
            df_filtered["Mã SV"].str.lower().str.contains(q, na=False)
        ]

    if class_filter:
        df_filtered = df_filtered[df_filtered["Lớp"].isin(class_filter)]

    display_cols = ["Họ tên", "Mã SV", "Lớp", "Trạng thái", "Check-in", "Check-out", "Similarity", "Liveness"]
    df_display = df_filtered[[c for c in display_cols if c in df_filtered.columns]].copy()

    styled = df_display.style.map(_color_status, subset=["Trạng thái"])
    st.dataframe(styled, use_container_width=True, height=400)

    # ── Export ────────────────────────────────────────────────────────────
    st.markdown("---")
    col_e1, col_e2 = st.columns(2)

    with col_e1:
        csv_bytes = df_filtered.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            label="📥 Xuất CSV",
            data=csv_bytes,
            file_name=f"attendance_{date_str}.csv",
            mime="text/csv",
        )

    with col_e2:
        try:
            excel_buf = io.BytesIO()
            with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
                df_filtered.to_excel(writer, index=False, sheet_name="Attendance")
            excel_bytes = excel_buf.getvalue()
            st.download_button(
                label="📥 Xuất Excel",
                data=excel_bytes,
                file_name=f"attendance_{date_str}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except ImportError:
            st.caption("Cài openpyxl để xuất Excel: `pip install openpyxl`")
