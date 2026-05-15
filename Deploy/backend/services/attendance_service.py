"""
Attendance check-in / check-out – CSV-backed storage.

One file per day: data/attendance/attendance_YYYY-MM-DD.csv
One row per person per day (upserted, never duplicated).

attendance_status values:
  CHECKED_IN   – has check_in_time, no check_out_time
  CHECKED_OUT  – has both check_in_time and check_out_time
  (ABSENT is derived at report time from active people not in the file)
"""

from __future__ import annotations

import json
from datetime import datetime, date, timezone, timedelta
from pathlib import Path

import pandas as pd

from backend.config import (
    ATTENDANCE_DIR,
    PEOPLE_CSV_PATH,
    RECENT_EVENTS_PATH,
    ensure_dirs,
)
from backend.services.person_service import get_person, get_all_people

ATTENDANCE_COLUMNS = [
    "date", "person_id", "full_name", "student_code", "class_name",
    "check_in_time", "check_out_time",
    "check_in_similarity", "check_out_similarity",
    "check_in_liveness_status", "check_out_liveness_status",
    "face_real_score", "full_real_score",
    "attendance_status", "created_at", "updated_at",
]

MAX_RECENT_EVENTS = 50


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    vn_tz = timezone(timedelta(hours=7))
    return datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S")


def _today_str() -> str:
    vn_tz = timezone(timedelta(hours=7))
    return datetime.now(vn_tz).strftime("%Y-%m-%d")


def _attendance_path(date_str: str) -> Path:
    ensure_dirs()
    return ATTENDANCE_DIR / f"attendance_{date_str}.csv"


def _load_day(date_str: str) -> pd.DataFrame:
    path = _attendance_path(date_str)
    if not path.exists():
        return pd.DataFrame(columns=ATTENDANCE_COLUMNS)
    try:
        df = pd.read_csv(path, encoding="utf-8-sig", dtype=str).fillna("")
        for col in ATTENDANCE_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        return df[ATTENDANCE_COLUMNS].copy()
    except Exception:
        return pd.DataFrame(columns=ATTENDANCE_COLUMNS)


def _save_day(date_str: str, df: pd.DataFrame) -> None:
    ensure_dirs()
    path = _attendance_path(date_str)
    tmp = path.with_suffix(".tmp")
    df[ATTENDANCE_COLUMNS].to_csv(tmp, index=False, encoding="utf-8-sig")
    tmp.replace(path)


def _row_to_dict(row: pd.Series) -> dict:
    return {k: ("" if pd.isna(v) else v) for k, v in row.items()}


def _nonempty_time_cell(val) -> bool:
    """True if attendance CSV time cell has a real timestamp string."""
    if val is None:
        return False
    try:
        if pd.isna(val):
            return False
    except TypeError:
        pass
    s = str(val).strip()
    if not s:
        return False
    low = s.lower()
    if low in ("nan", "nat", "none", "<na>", "null"):
        return False
    return True


# ---------------------------------------------------------------------------
# Recent events feed
# ---------------------------------------------------------------------------

def _append_recent_event(event: dict) -> None:
    """Prepend event to recent_events.json, keep last MAX_RECENT_EVENTS."""
    ensure_dirs()
    events: list = []
    if RECENT_EVENTS_PATH.exists():
        try:
            with open(RECENT_EVENTS_PATH, encoding="utf-8") as f:
                events = json.load(f)
        except Exception:
            events = []

    events.insert(0, event)
    events = events[:MAX_RECENT_EVENTS]

    tmp = RECENT_EVENTS_PATH.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    tmp.replace(RECENT_EVENTS_PATH)


def get_recent_attendance_summary(days: int = 30) -> dict[str, dict]:
    """
    Scan the last `days` attendance files and return the most recent record
    per person:  {person_id: {last_check_in, last_check_out, last_date}}
    """
    from datetime import timedelta, date as _date
    summary: dict[str, dict] = {}
    today = _date.today()
    for i in range(days):
        d   = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        path = _attendance_path(d)
        if not path.exists():
            continue
        df = _load_day(d)
        for _, row in df.iterrows():
            pid = str(row.get("person_id", "")).strip()
            if not pid or pid in summary:
                continue          # first hit = most recent (iterating newest first)
            summary[pid] = {
                "last_check_in":  str(row.get("check_in_time",  "") or ""),
                "last_check_out": str(row.get("check_out_time", "") or ""),
                "last_date":      d,
            }
    return summary


def get_person_attendance_history(person_id: str, days: int = 7) -> list[dict]:
    """
    Return attendance records for one person over the past `days` days.
    days=0 means all records ever found.
    """
    from datetime import timedelta, date as _date
    records: list[dict] = []

    if days <= 0:
        att_files  = sorted(ATTENDANCE_DIR.glob("attendance_*.csv"), reverse=True)
        date_strs  = [f.stem.replace("attendance_", "") for f in att_files]
    else:
        today      = _date.today()
        date_strs  = [(today - timedelta(days=i)).strftime("%Y-%m-%d")
                      for i in range(days)]

    for date_str in date_strs:
        df   = _load_day(date_str)
        mask = df["person_id"] == person_id
        if mask.any():
            row = df[mask].iloc[0].to_dict()
            row.setdefault("date", date_str)
            records.append(row)

    return records


def get_recent_events(limit: int = 20) -> list[dict]:
    if not RECENT_EVENTS_PATH.exists():
        return []
    try:
        with open(RECENT_EVENTS_PATH, encoding="utf-8") as f:
            events = json.load(f)
        return events[:limit]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Check-in
# ---------------------------------------------------------------------------

def check_in(
    person_id: str,
    similarity: float = 0.0,
    liveness_status: str = "REAL_ATTENDANCE_OK",
    face_real_score: float = 0.0,
    full_real_score: float = 0.0,
) -> dict:
    """
    Returns:
      ok=True,  action=CHECKED_IN
      ok=False, action=ALREADY_CHECKED_IN
      ok=False, action=PERSON_NOT_FOUND
      ok=False, action=PERSON_INACTIVE
    """
    person = get_person(person_id)
    if not person:
        return {"ok": False, "action": "PERSON_NOT_FOUND",
                "message": "Người không tồn tại"}

    if person.get("status", "inactive") != "active":
        return {"ok": False, "action": "PERSON_INACTIVE",
                "message": "Người dùng không hoạt động"}

    today = _today_str()
    now   = _now()
    df    = _load_day(today)

    mask = df["person_id"] == person_id

    if mask.any():
        # Row already exists – they already checked in
        row = _row_to_dict(df[mask].iloc[0])
        return {"ok": False, "action": "ALREADY_CHECKED_IN", "record": row,
                "message": f"Bạn đã điểm danh hôm nay rồi"}

    # Create new row
    new_row = pd.DataFrame([{
        "date":                    today,
        "person_id":               person_id,
        "full_name":               person.get("full_name", ""),
        "student_code":            person.get("student_code", ""),
        "class_name":              person.get("class_name", ""),
        "check_in_time":           now,
        "check_out_time":          "",
        "check_in_similarity":     str(round(similarity, 4)),
        "check_out_similarity":    "",
        "check_in_liveness_status":  liveness_status,
        "check_out_liveness_status": "",
        "face_real_score":         str(round(face_real_score, 4)),
        "full_real_score":         str(round(full_real_score, 4)),
        "attendance_status":       "CHECKED_IN",
        "created_at":              now,
        "updated_at":              now,
    }])

    df = pd.concat([df, new_row], ignore_index=True)
    _save_day(today, df)

    record = _row_to_dict(df[df["person_id"] == person_id].iloc[0])

    _append_recent_event({
        "event_type":      "CHECK_IN",
        "event_time":      now,
        "person_id":       person_id,
        "full_name":       person.get("full_name", ""),
        "student_code":    person.get("student_code", ""),
        "similarity":      round(similarity, 4),
        "liveness_status": liveness_status,
        "attendance_status": "CHECKED_IN",
    })

    return {"ok": True, "action": "CHECKED_IN", "record": record,
            "message": f"Check in thành công: {person.get('full_name', person_id)}"}


# ---------------------------------------------------------------------------
# Check-out
# ---------------------------------------------------------------------------

def check_out(
    person_id: str,
    similarity: float = 0.0,
    liveness_status: str = "REAL_ATTENDANCE_OK",
    face_real_score: float = 0.0,
    full_real_score: float = 0.0,
) -> dict:
    """
    Returns:
      ok=True,  action=CHECKED_OUT
      ok=False, action=NOT_CHECKED_IN
      ok=False, action=ALREADY_CHECKED_OUT
      ok=False, action=PERSON_NOT_FOUND
      ok=False, action=PERSON_INACTIVE
    """
    person = get_person(person_id)
    if not person:
        return {"ok": False, "action": "PERSON_NOT_FOUND",
                "message": "Người không tồn tại"}

    if person.get("status", "inactive") != "active":
        return {"ok": False, "action": "PERSON_INACTIVE",
                "message": "Người dùng không hoạt động"}

    today = _today_str()
    now   = _now()
    df    = _load_day(today)

    mask = df["person_id"] == person_id

    if not mask.any():
        return {"ok": False, "action": "NOT_CHECKED_IN",
                "message": "Bạn chưa check in hôm nay"}

    row = _row_to_dict(df[mask].iloc[0])
    if not _nonempty_time_cell(row.get("check_in_time")):
        return {"ok": False, "action": "NOT_CHECKED_IN",
                "message": "Bạn chưa check in hôm nay"}

    if _nonempty_time_cell(row.get("check_out_time")):
        return {"ok": False, "action": "ALREADY_CHECKED_OUT", "record": row,
                "message": "Bạn đã check out hôm nay rồi"}

    # Update existing row
    df.loc[mask, "check_out_time"]           = now
    df.loc[mask, "check_out_similarity"]     = str(round(similarity, 4))
    df.loc[mask, "check_out_liveness_status"] = liveness_status
    df.loc[mask, "attendance_status"]        = "CHECKED_OUT"
    df.loc[mask, "updated_at"]               = now

    _save_day(today, df)

    record = _row_to_dict(df[df["person_id"] == person_id].iloc[0])

    _append_recent_event({
        "event_type":      "CHECK_OUT",
        "event_time":      now,
        "person_id":       person_id,
        "full_name":       person.get("full_name", ""),
        "student_code":    person.get("student_code", ""),
        "similarity":      round(similarity, 4),
        "liveness_status": liveness_status,
        "attendance_status": "CHECKED_OUT",
    })

    return {"ok": True, "action": "CHECKED_OUT", "record": record,
            "message": f"Check out thành công: {person.get('full_name', person_id)}"}


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def get_attendance_by_date(date_str: str) -> list[dict]:
    """Return all rows in the attendance CSV for a date."""
    df = _load_day(date_str)
    return df.to_dict(orient="records")


def get_today_attendance() -> list[dict]:
    return get_attendance_by_date(_today_str())


def get_attendance_report(date_str: str) -> dict:
    """
    Returns present/absent/checked-out breakdown.
    ABSENT = active person has no row in the day's CSV.
    """
    all_people   = get_all_people()
    active_people = [p for p in all_people if p.get("status") == "active"]

    att_rows  = {r["person_id"]: r for r in get_attendance_by_date(date_str)}

    present     = []
    checked_out = []
    absent      = []

    for p in active_people:
        pid = p["person_id"]
        rec = att_rows.get(pid)
        if rec:
            if rec.get("attendance_status") == "CHECKED_OUT":
                checked_out.append(rec)
            else:
                present.append(rec)
        else:
            absent.append({**p, "attendance_status": "ABSENT", "date": date_str})

    return {
        "date":              date_str,
        "total_active":      len(active_people),
        "present_count":     len(present),
        "checked_out_count": len(checked_out),
        "absent_count":      len(absent),
        "present":           present,
        "checked_out":       checked_out,
        "absent":            absent,
    }
