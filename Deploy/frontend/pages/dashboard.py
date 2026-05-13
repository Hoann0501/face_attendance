"""
Dashboard page – overview metrics + recent activity feed.
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
from datetime import date

from backend.config import BACKEND_URL


def _api(path: str, default=None):
    try:
        r = requests.get(f"{BACKEND_URL}{path}", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.warning(f"API error: {e}")
        return default


def show():
    st.title("📊 Dashboard")

    # Auto-refresh every 5 seconds
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=5000, key="dashboard_refresh")
    except ImportError:
        pass

    # ── Metrics ──────────────────────────────────────────────────────────
    today_str = date.today().isoformat()
    report = _api(f"/attendance/report?date={today_str}", default={})
    people_data = _api("/people", default=[])

    total = len(people_data) if people_data else 0
    active = sum(1 for p in (people_data or []) if p.get("status") == "active")
    inactive = total - active
    present = report.get("present_count", 0)
    absent = report.get("absent_count", 0)
    checked_out = report.get("checked_out_count", 0)

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Tổng người", total)
    col2.metric("Active", active)
    col3.metric("Inactive", inactive)
    col4.metric("Check-in hôm nay", present + checked_out)
    col5.metric("Check-out hôm nay", checked_out)
    col6.metric("Vắng", absent)

    st.markdown("---")

    # ── Recent events ─────────────────────────────────────────────────────
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.subheader("Hoạt động gần đây")
        events_data = _api("/attendance/events/recent?limit=15", default={"events": []})
        events = events_data.get("events", []) if events_data else []

        if events:
            df = pd.DataFrame(events)
            display_cols = [c for c in ["event_time", "event_type", "full_name", "student_code", "similarity", "liveness_status"] if c in df.columns]
            df_display = df[display_cols].copy()

            def color_event(val):
                if val == "CHECK_IN":
                    return "background-color: #1a5c1a; color: white"
                if val == "CHECK_OUT":
                    return "background-color: #1a3fa0; color: white"
                return ""

            if "event_type" in df_display.columns:
                styled = df_display.style.map(color_event, subset=["event_type"])
                st.dataframe(styled, use_container_width=True, height=350)
            else:
                st.dataframe(df_display, use_container_width=True, height=350)
        else:
            st.info("Chưa có hoạt động nào hôm nay.")

    with col_right:
        st.subheader(f"Điểm danh hôm nay – {today_str}")

        present_list = report.get("present", [])
        absent_list = report.get("absent", [])
        co_list = report.get("checked_out", [])

        all_records = []
        for r in present_list:
            all_records.append({
                "Họ tên": r.get("full_name", ""),
                "Mã SV": r.get("student_code", ""),
                "Lớp": r.get("class_name", ""),
                "Trạng thái": "PRESENT",
                "Check-in": r.get("check_in_time", "")[:19] if r.get("check_in_time") else "",
            })
        for r in co_list:
            all_records.append({
                "Họ tên": r.get("full_name", ""),
                "Mã SV": r.get("student_code", ""),
                "Lớp": r.get("class_name", ""),
                "Trạng thái": "CHECKED_OUT",
                "Check-in": r.get("check_in_time", "")[:19] if r.get("check_in_time") else "",
            })
        for r in absent_list:
            all_records.append({
                "Họ tên": r.get("full_name", ""),
                "Mã SV": r.get("student_code", ""),
                "Lớp": r.get("class_name", ""),
                "Trạng thái": "ABSENT",
                "Check-in": "",
            })

        if all_records:
            df2 = pd.DataFrame(all_records)

            def color_status(val):
                if val == "PRESENT":
                    return "background-color: #1a5c1a; color: white; font-weight: bold"
                if val == "ABSENT":
                    return "background-color: #8b0000; color: white; font-weight: bold"
                if val == "CHECKED_OUT":
                    return "background-color: #1a3fa0; color: white; font-weight: bold"
                return ""

            styled2 = df2.style.map(color_status, subset=["Trạng thái"])
            st.dataframe(styled2, use_container_width=True, height=350)
        else:
            st.info("Chưa có dữ liệu.")

    # ── Health ────────────────────────────────────────────────────────────
    with st.expander("API Health"):
        health = _api("/health", default={"status": "unreachable"})
        if health and health.get("status") == "ok":
            st.success(f"Backend OK – {health.get('timestamp', '')}")
        else:
            st.error("Backend không phản hồi. Kiểm tra run_backend.bat")
