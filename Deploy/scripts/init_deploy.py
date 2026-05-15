"""
Initialize the Deploy project (CSV-based storage):
1. Ensure all data directories exist
2. Seed people.csv from data/people/people.csv (already in place after copy)
3. Migrate old attendance CSV logs from data/attendance_logs/ into data/attendance/

Run once before first launch:
    python scripts/init_deploy.py
"""

from __future__ import annotations

import sys
import csv
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta

DEPLOY_ROOT = Path(__file__).resolve().parent.parent
if str(DEPLOY_ROOT) not in sys.path:
    sys.path.insert(0, str(DEPLOY_ROOT))

from backend.config import (
    ensure_dirs,
    DATA_DIR,
    PEOPLE_DIR,
    PEOPLE_CSV_PATH,
    ATTENDANCE_DIR,
    REPORTS_DIR,
    ENROLL_IMAGES_DIR,
    RUNTIME_DIR,
)
from backend.services.person_service import upsert_person, get_all_people

# Old attendance logs might still live here (from the copy step)
OLD_LOGS_DIR = DATA_DIR / "attendance_logs"


# ---------------------------------------------------------------------------

def _ensure_people_csv():
    """
    If people.csv doesn't have the new columns (created_at / updated_at),
    re-save it with those columns added.
    """
    if not PEOPLE_CSV_PATH.exists():
        print("[init] people.csv not found – skipping.")
        return

    import pandas as pd
    df = pd.read_csv(PEOPLE_CSV_PATH, encoding="utf-8-sig", dtype=str).fillna("")

    vn_tz = timezone(timedelta(hours=7))
    now = datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S")
    if "created_at" not in df.columns:
        df["created_at"] = now
    if "updated_at" not in df.columns:
        df["updated_at"] = now

    from backend.services.person_service import PEOPLE_COLUMNS
    for col in PEOPLE_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df[PEOPLE_COLUMNS].to_csv(PEOPLE_CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"[init] people.csv normalised – {len(df)} people.")


def _migrate_old_logs():
    """
    Convert old-format attendance CSVs
    (timestamp, person_id, ..., attendance_status, similarity, liveness_status, ...)
    into the new per-day format under data/attendance/.
    """
    src_dir = OLD_LOGS_DIR
    if not src_dir.exists():
        print("[init] No old attendance_logs dir – nothing to migrate.")
        return

    log_files = sorted(src_dir.glob("attendance_*.csv"))
    if not log_files:
        print("[init] No old attendance CSV files found.")
        return

    from backend.services.attendance_service import (
        ATTENDANCE_COLUMNS, _load_day, _save_day, _attendance_path
    )
    import pandas as pd

    total = 0
    for src_path in log_files:
        try:
            df_old = pd.read_csv(src_path, encoding="utf-8-sig", dtype=str).fillna("")
        except Exception as e:
            print(f"  [warn] Cannot read {src_path.name}: {e}")
            continue

        for _, row in df_old.iterrows():
            person_id = str(row.get("person_id", "")).strip()
            timestamp  = str(row.get("timestamp", "")).strip()
            if not person_id or not timestamp:
                continue

            date_str  = timestamp[:10]
            sim       = row.get("similarity", "0")
            liveness  = row.get("liveness_status", "REAL_ATTENDANCE_OK")
            face_r    = row.get("face_real_score", "0")
            full_r    = row.get("full_real_score", "0")
            full_name = str(row.get("full_name", "")).strip()
            scode     = str(row.get("student_code", "")).strip()
            cname     = str(row.get("class_name", "")).strip()

            day_df = _load_day(date_str)
            if (day_df["person_id"] == person_id).any():
                # Already migrated
                continue

            vn_tz = timezone(timedelta(hours=7))
            now = datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S")
            new_row = pd.DataFrame([{
                "date":                    date_str,
                "person_id":               person_id,
                "full_name":               full_name,
                "student_code":            scode,
                "class_name":              cname,
                "check_in_time":           timestamp,
                "check_out_time":          "",
                "check_in_similarity":     sim,
                "check_out_similarity":    "",
                "check_in_liveness_status":  liveness,
                "check_out_liveness_status": "",
                "face_real_score":         face_r,
                "full_real_score":         full_r,
                "attendance_status":       "CHECKED_IN",
                "created_at":              now,
                "updated_at":              now,
            }])

            day_df = pd.concat([day_df, new_row], ignore_index=True)
            _save_day(date_str, day_df)
            total += 1

    print(f"[init] Migrated {total} attendance records -> data/attendance/")


def main():
    print("=" * 60)
    print("[init] Initializing Deploy project (CSV mode) ...")
    print(f"[init] DEPLOY_ROOT = {DEPLOY_ROOT}")

    print("[init] Creating directories ...")
    ensure_dirs()

    print("[init] Normalising people.csv ...")
    _ensure_people_csv()

    print("[init] Migrating old attendance logs ...")
    _migrate_old_logs()

    people = get_all_people()
    print(f"[init] Done! people.csv has {len(people)} people.")

    att_files = list((DATA_DIR / "attendance").glob("attendance_*.csv"))
    print(f"[init] Attendance files: {len(att_files)}")

    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Start backend:  scripts\\run_backend.bat")
    print("  2. Start frontend: scripts\\run_frontend.bat")
    print("  3. Start camera:   scripts\\run_camera_checkin.bat")


if __name__ == "__main__":
    main()
