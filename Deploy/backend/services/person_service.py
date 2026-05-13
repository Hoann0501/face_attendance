"""
People CRUD – CSV-backed storage.
File: data/people/people.csv
Columns: person_id,full_name,student_code,class_name,status,created_at,updated_at
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from backend.config import PEOPLE_CSV_PATH, ensure_dirs

PEOPLE_COLUMNS = [
    "person_id", "full_name", "student_code", "class_name",
    "status", "created_at", "updated_at",
]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# Low-level I/O
# ---------------------------------------------------------------------------

def _load_df() -> pd.DataFrame:
    ensure_dirs()
    if not PEOPLE_CSV_PATH.exists():
        return pd.DataFrame(columns=PEOPLE_COLUMNS)
    try:
        df = pd.read_csv(PEOPLE_CSV_PATH, encoding="utf-8-sig", dtype=str).fillna("")
        for col in PEOPLE_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        return df[PEOPLE_COLUMNS].copy()
    except Exception:
        return pd.DataFrame(columns=PEOPLE_COLUMNS)


def _save_df(df: pd.DataFrame) -> None:
    ensure_dirs()
    tmp = PEOPLE_CSV_PATH.with_suffix(".tmp")
    df[PEOPLE_COLUMNS].to_csv(tmp, index=False, encoding="utf-8-sig")
    tmp.replace(PEOPLE_CSV_PATH)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_all_people() -> list[dict]:
    return _load_df().to_dict(orient="records")


def get_person(person_id: str) -> dict | None:
    df = _load_df()
    mask = df["person_id"] == person_id
    if not mask.any():
        return None
    return df[mask].iloc[0].to_dict()


def create_person(
    person_id: str,
    full_name: str = "",
    student_code: str = "",
    class_name: str = "",
    status: str = "active",
) -> dict:
    df = _load_df()
    now = _now()
    new_row = pd.DataFrame([{
        "person_id": person_id,
        "full_name": full_name,
        "student_code": student_code,
        "class_name": class_name,
        "status": status,
        "created_at": now,
        "updated_at": now,
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    _save_df(df)
    return get_person(person_id)


def update_person(person_id: str, **kwargs) -> dict | None:
    df = _load_df()
    mask = df["person_id"] == person_id
    if not mask.any():
        return None
    allowed = {"full_name", "student_code", "class_name", "status"}
    for k, v in kwargs.items():
        if k in allowed and v is not None:
            df.loc[mask, k] = v
    df.loc[mask, "updated_at"] = _now()
    _save_df(df)
    return get_person(person_id)


def upsert_person(
    person_id: str,
    full_name: str = "",
    student_code: str = "",
    class_name: str = "",
    status: str = "active",
) -> dict:
    df = _load_df()
    now = _now()
    mask = df["person_id"] == person_id
    if mask.any():
        df.loc[mask, "full_name"]     = full_name
        df.loc[mask, "student_code"]  = student_code
        df.loc[mask, "class_name"]    = class_name
        df.loc[mask, "status"]        = status
        df.loc[mask, "updated_at"]    = now
    else:
        new_row = pd.DataFrame([{
            "person_id": person_id,
            "full_name": full_name,
            "student_code": student_code,
            "class_name": class_name,
            "status": status,
            "created_at": now,
            "updated_at": now,
        }])
        df = pd.concat([df, new_row], ignore_index=True)
    _save_df(df)
    return get_person(person_id)


def delete_person(person_id: str) -> bool:
    df = _load_df()
    before = len(df)
    df = df[df["person_id"] != person_id].copy()
    _save_df(df)
    return len(df) < before


def patch_person_status(person_id: str, status: str) -> dict | None:
    return update_person(person_id, status=status)
