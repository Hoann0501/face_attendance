"""
Central configuration for the Deploy project.
All paths are derived from DEPLOY_ROOT so the project is fully portable.
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Root directory
# ---------------------------------------------------------------------------

# When running from Deploy/, this resolves to Deploy/
DEPLOY_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Data paths  (flat file storage – no SQL/SQLite)
# ---------------------------------------------------------------------------

DATA_DIR              = DEPLOY_ROOT / "data"
PEOPLE_DIR            = DATA_DIR / "people"
ATTENDANCE_DIR        = DATA_DIR / "attendance"
REPORTS_DIR           = DATA_DIR / "reports"
ENROLL_IMAGES_DIR     = DATA_DIR / "enroll_images"
RUNTIME_DIR           = DATA_DIR / "runtime"

PEOPLE_CSV_PATH       = PEOPLE_DIR / "people.csv"
RECENT_EVENTS_PATH    = RUNTIME_DIR / "recent_events.json"

FACE_CAPTURES_DIR     = DATA_DIR / "face_captures"

# ---------------------------------------------------------------------------
# Model paths
# ---------------------------------------------------------------------------

MODELS_DIR = DEPLOY_ROOT / "models"

ANTI_SPOOF_MODEL_PATH = MODELS_DIR / "anti_spoof" / "vfa_mobilenetv3_small_best.pth"
ANTI_SPOOF_CONFIG_PATH = MODELS_DIR / "anti_spoof" / "vfa_deploy_config.json"

TEMPLATES_PATH        = MODELS_DIR / "verification" / "person_templates.pkl"
VERIFY_CONFIG_PATH    = MODELS_DIR / "verification" / "face_verification_config.json"

ATTRIBUTE_MODEL_PATH  = MODELS_DIR / "attribute" / "face_attribute_mobilenetv3_best.pth"
ATTRIBUTE_CONFIG_PATH = MODELS_DIR / "attribute" / "face_attribute_config.json"

# ---------------------------------------------------------------------------
# Anti-spoofing thresholds
# ---------------------------------------------------------------------------

REAL_THRESHOLD_FACE: float = float(os.getenv("REAL_THRESHOLD_FACE", "0.75"))
REAL_THRESHOLD_FULL: float = float(os.getenv("REAL_THRESHOLD_FULL", "0.55"))
WINDOW_SIZE: int           = int(os.getenv("WINDOW_SIZE", "7"))
MIN_REAL_VOTES: int        = int(os.getenv("MIN_REAL_VOTES", "5"))

# ---------------------------------------------------------------------------
# Face verification
# ---------------------------------------------------------------------------

VERIFY_THRESHOLD: float = float(os.getenv("VERIFY_THRESHOLD", "0.35"))
FACE_TOP_K: int         = int(os.getenv("FACE_TOP_K", "5"))

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

BACKEND_HOST: str = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
BACKEND_URL: str  = f"http://{BACKEND_HOST}:{BACKEND_PORT}"

# ---------------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------------

CAMERA_INDEX: int            = int(os.getenv("CAMERA_INDEX", "0"))
CAMERA_COOLDOWN_SECONDS: int = int(os.getenv("CAMERA_COOLDOWN_SECONDS", "4"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ensure_dirs():
    """Create all required data directories if they don't exist."""
    for d in [
        PEOPLE_DIR,
        ATTENDANCE_DIR,
        REPORTS_DIR,
        ENROLL_IMAGES_DIR,
        RUNTIME_DIR,
        FACE_CAPTURES_DIR,
    ]:
        d.mkdir(parents=True, exist_ok=True)
