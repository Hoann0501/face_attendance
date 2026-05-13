"""
Face Attendance Deploy – FastAPI backend entry point.

Run with:
    python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
"""

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

STATIC_DIR = Path(__file__).parent.parent / "frontend" / "static"

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

@app.get("/", include_in_schema=False)
def serve_spa():
    return FileResponse(str(STATIC_DIR / "index.html"))

# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

@app.on_event("startup")
def startup_event():
    print("[Backend] Initializing database ...")
    init_db()
    print(f"[Backend] Frontend: http://127.0.0.1:8000")
    print("[Backend] API docs: http://127.0.0.1:8000/docs")
    print("[Backend] Ready.")
