"""
Camera app configuration – all settings in one place.
"""

from __future__ import annotations

import sys
from pathlib import Path

DEPLOY_ROOT = Path(__file__).resolve().parent.parent
if str(DEPLOY_ROOT) not in sys.path:
    sys.path.insert(0, str(DEPLOY_ROOT))

from backend.config import (
    ANTI_SPOOF_MODEL_PATH,
    TEMPLATES_PATH,
    VERIFY_CONFIG_PATH,
    REAL_THRESHOLD_FACE,
    REAL_THRESHOLD_FULL,
    WINDOW_SIZE,
    MIN_REAL_VOTES,
    VERIFY_THRESHOLD,
    BACKEND_URL,
    CAMERA_INDEX,
    CAMERA_COOLDOWN_SECONDS,
)

# Re-export so camera_app only imports from camera_config
__all__ = [
    "DEPLOY_ROOT",
    "ANTI_SPOOF_MODEL_PATH",
    "TEMPLATES_PATH",
    "VERIFY_CONFIG_PATH",
    "REAL_THRESHOLD_FACE",
    "REAL_THRESHOLD_FULL",
    "WINDOW_SIZE",
    "MIN_REAL_VOTES",
    "VERIFY_THRESHOLD",
    "BACKEND_URL",
    "CAMERA_INDEX",
    "CAMERA_COOLDOWN_SECONDS",
]

# Camera display
WINDOW_TITLE = "Face Attendance Camera"
BBOX_COLOR_REAL = (0, 255, 0)      # Green
BBOX_COLOR_FAKE = (0, 0, 255)      # Red
BBOX_COLOR_CHECKING = (0, 200, 200)  # Cyan
BBOX_THICKNESS = 2
