"""
Face Attendance Deploy – FastAPI backend entry point.

Run with (chỉ máy local):
    python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

Demo cùng mạng LAN (điện thoại / laptop khác vào web):
    python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
    # Rồi mở http://<IPv4-máy-chạy-server>:8000 — có thể cần mở Firewall Windows cho cổng 8000.
"""

import os
import socket
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.database import init_db
from backend.api.health import router as health_router
from backend.api.people import router as people_router
from backend.api.attendance import router as attendance_router
from backend.api.face import router as face_router

STATIC_DIR    = Path(__file__).parent.parent / "frontend" / "static"
CAPTURES_DIR  = Path(__file__).parent.parent / "data" / "face_captures"

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Face Attendance API",
    description="Backend API for face recognition attendance system",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(health_router)
app.include_router(people_router)
app.include_router(attendance_router)
app.include_router(face_router)

# Serve static frontend
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static_files")

# face_captures directory is served via /attendance/captures/image endpoint (see attendance.py)
CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

@app.get("/", include_in_schema=False)
def serve_spa():
    return FileResponse(str(STATIC_DIR / "index.html"))

# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

def _guess_lan_ipv4() -> str | None:
    """Best-effort LAN address for demo links (UDP socket; no traffic sent)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.25)
        s.connect(("203.0.113.1", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip.startswith("127."):
            return None
        return ip
    except OSError:
        return None


@app.on_event("startup")
def startup_event():
    port = int(os.getenv("BACKEND_PORT", "8000"))
    print("[Backend] Initializing database ...")
    init_db()
    print(f"[Backend] Local:   http://127.0.0.1:{port}/")
    lan = _guess_lan_ipv4()
    if lan:
        print(f"[Backend] LAN:     http://{lan}:{port}/  (may khac cung Wi-Fi mo URL nay)")
        print("[Backend] Neu khong vao duoc: mo Firewall Windows cho python.exe hoac cong", port)
    print(f"[Backend] API docs: http://127.0.0.1:{port}/docs")
    print("[Backend] Ready.")
