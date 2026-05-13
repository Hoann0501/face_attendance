"""
Re-run data migration (people + old attendance logs) at any time.
Safe to run multiple times – existing rows are not overwritten.

    python scripts/import_existing_data.py
"""

from __future__ import annotations

import sys
from pathlib import Path

DEPLOY_ROOT = Path(__file__).resolve().parent.parent
if str(DEPLOY_ROOT) not in sys.path:
    sys.path.insert(0, str(DEPLOY_ROOT))

from scripts.init_deploy import _ensure_people_csv, _migrate_old_logs

print("[migrate] Re-running data import ...")
_ensure_people_csv()
_migrate_old_logs()
print("[migrate] Done.")
