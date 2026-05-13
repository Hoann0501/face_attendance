"""
Storage layer – flat CSV files (no SQL/SQLite).

This module is kept as a thin compatibility shim so imports don't break.
The actual I/O logic lives in the service modules.
"""

from backend.config import ensure_dirs


def init_db():
    """No-op: ensure data directories exist."""
    ensure_dirs()
    print("[Storage] Using flat CSV files. Directories ready.")
