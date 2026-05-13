"""
Face Attendance – Streamlit Web Management App.

Run with:
    python -m streamlit run frontend/app.py
"""

import sys
from pathlib import Path

# Ensure Deploy root is on sys.path so imports work
DEPLOY_ROOT = Path(__file__).resolve().parent.parent
if str(DEPLOY_ROOT) not in sys.path:
    sys.path.insert(0, str(DEPLOY_ROOT))

import streamlit as st

st.set_page_config(
    page_title="Face Attendance",
    page_icon="🧑‍💻",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject global CSS
def _load_css():
    css_path = Path(__file__).parent / "assets" / "styles.css"
    if css_path.exists():
        with open(css_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

_load_css()

# Navigation
from frontend.pages import (
    dashboard,
    people,
    register,
    face_search,
    face_analysis,
    attendance_report,
)

PAGES = {
    "📊 Dashboard": dashboard,
    "👥 Quản lý người": people,
    "📸 Đăng ký khuôn mặt": register,
    "🔍 Tìm kiếm / Xác minh": face_search,
    "🧬 Phân tích ảnh": face_analysis,
    "📋 Báo cáo điểm danh": attendance_report,
}

st.sidebar.title("🧑‍💻 Face Attendance")
st.sidebar.markdown("---")

choice = st.sidebar.radio("Điều hướng", list(PAGES.keys()))

st.sidebar.markdown("---")
from backend.config import BACKEND_URL
st.sidebar.caption(f"Backend: `{BACKEND_URL}`")

PAGES[choice].show()
