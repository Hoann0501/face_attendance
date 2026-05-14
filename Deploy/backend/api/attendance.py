import io
import re
from pathlib import Path
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from typing import Optional
from datetime import date
import pandas as pd

from backend.config import FACE_CAPTURES_DIR

from backend.schemas import AttendanceCheckIn, AttendanceCheckOut, AttendanceRecord, AttendanceEvent
from backend.services import attendance_service as svc

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("/check-in")
def check_in(body: AttendanceCheckIn):
    result = svc.check_in(
        person_id=body.person_id,
        similarity=body.similarity,
        liveness_status=body.liveness_status,
        face_real_score=body.face_real_score,
        full_real_score=body.full_real_score,
    )
    if not result["ok"]:
        action = result.get("action", "")
        if action == "PERSON_NOT_FOUND":
            raise HTTPException(status_code=404, detail=result["message"])
        if action == "PERSON_INACTIVE":
            raise HTTPException(status_code=403, detail=result["message"])
        # ALREADY_CHECKED_IN – return 200 with message
        return result
    return result


@router.post("/check-out")
def check_out(body: AttendanceCheckOut):
    result = svc.check_out(
        person_id=body.person_id,
        similarity=body.similarity,
        liveness_status=body.liveness_status,
        face_real_score=body.face_real_score,
        full_real_score=body.full_real_score,
    )
    if not result["ok"]:
        action = result.get("action", "")
        if action == "PERSON_NOT_FOUND":
            raise HTTPException(status_code=404, detail=result["message"])
        if action == "PERSON_INACTIVE":
            raise HTTPException(status_code=403, detail=result["message"])
        return result
    return result


@router.get("/today")
def today_attendance():
    rows = svc.get_today_attendance()
    return {"date": date.today().isoformat(), "records": rows, "count": len(rows)}


@router.get("/events/recent")
def recent_events(limit: int = Query(default=20, ge=1, le=100)):
    events = svc.get_recent_events(limit=limit)
    return {"events": events, "count": len(events)}


@router.get("/report")
def attendance_report(date: Optional[str] = Query(default=None)):
    date_str = date or svc._today_str()
    try:
        _validate_date(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    return svc.get_attendance_report(date_str)


@router.get("")
def attendance_by_date(date: Optional[str] = Query(default=None)):
    date_str = date or svc._today_str()
    try:
        _validate_date(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    rows = svc.get_attendance_by_date(date_str)
    return {"date": date_str, "records": rows, "count": len(rows)}


@router.delete("")
def delete_attendance(
    person_id: str = Query(...),
    date: Optional[str] = Query(default=None),
):
    """
    Delete attendance record for a specific person on a given date,
    including any associated face capture images.
    """
    date_str = date or svc._today_str()
    try:
        _validate_date(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")

    from backend.config import ATTENDANCE_DIR
    path = ATTENDANCE_DIR / f"attendance_{date_str}.csv"

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"No attendance file for {date_str}")

    try:
        df = pd.read_csv(path, encoding="utf-8-sig", dtype=str).fillna("")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    before = len(df)
    df = df[df["person_id"] != person_id].copy()

    if len(df) == before:
        raise HTTPException(status_code=404, detail=f"{person_id} has no attendance record on {date_str}")

    # Write updated CSV
    tmp = path.with_suffix(".tmp")
    df.to_csv(tmp, index=False, encoding="utf-8-sig")
    tmp.replace(path)

    # Delete associated face capture images
    deleted_images = _delete_capture_images(person_id, date_str)

    return {
        "ok": True,
        "message": f"Deleted attendance for {person_id} on {date_str}",
        "deleted_images": deleted_images,
    }


def _delete_capture_images(person_id: str, date_str: str) -> list[str]:
    """
    Delete all face capture images for a given person and date.
    Matches files like: {person_id}_{YYYY-MM-DD}_{HH-MM-SS}_{mode}.jpg
    Returns list of deleted file names.
    """
    deleted = []
    day_dir = FACE_CAPTURES_DIR / date_str

    for mode in ("checkin", "checkout"):
        mode_dir = day_dir / mode
        if not mode_dir.exists():
            continue
        # Match all images whose stem starts with the person_id followed by underscore + date
        for img_path in mode_dir.glob("*.jpg"):
            pid, _ = _parse_capture_filename(img_path.stem)
            if pid == person_id:
                try:
                    img_path.unlink()
                    deleted.append(img_path.name)
                except Exception as e:
                    print(f"[API] Warning: could not delete {img_path}: {e}")

    if deleted:
        print(f"[API] Deleted {len(deleted)} capture image(s) for {person_id} on {date_str}: {deleted}")

    return deleted


@router.get("/export")
def export_attendance(
    date: Optional[str] = Query(default=None),
    fmt: str = Query(default="csv", alias="format"),
):
    date_str = date or svc._today_str()
    try:
        _validate_date(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")

    report = svc.get_attendance_report(date_str)

    rows = []
    for r in report.get("present", []):
        rows.append({**r, "attendance_status": "PRESENT"})
    for r in report.get("checked_out", []):
        rows.append({**r, "attendance_status": "CHECKED_OUT"})
    for r in report.get("absent", []):
        rows.append({**r, "attendance_status": "ABSENT"})

    df = pd.DataFrame(rows) if rows else pd.DataFrame()

    if fmt == "xlsx":
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df.to_excel(w, index=False, sheet_name="Attendance")
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=attendance_{date_str}.xlsx"},
        )

    csv_bytes = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=attendance_{date_str}.csv"},
    )


@router.get("/captures")
def list_captures(date: Optional[str] = Query(default=None)):
    """
    List all face capture images for a given date.
    Filename format: {person_id}_{YYYY-MM-DD}_{HH-MM-SS}_{mode}.jpg
    """
    date_str = date or svc._today_str()
    try:
        _validate_date(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")

    day_dir  = FACE_CAPTURES_DIR / date_str
    results  = []

    # Attendance data for name/code enrichment
    att_rows = {r["person_id"]: r for r in svc.get_attendance_by_date(date_str)}

    for mode in ["checkin", "checkout"]:
        mode_dir = day_dir / mode
        if not mode_dir.exists():
            continue
        for img_path in sorted(mode_dir.glob("*.jpg")):
            person_id, timestamp = _parse_capture_filename(img_path.stem)
            att = att_rows.get(person_id, {})
            results.append({
                "person_id":    person_id,
                "full_name":    att.get("full_name", ""),
                "student_code": att.get("student_code", ""),
                "mode":         mode,
                "filename":     img_path.name,
                # Use API endpoint instead of static mount — more reliable
                "url": f"/attendance/captures/image?date={date_str}&mode={mode}&filename={img_path.name}",
                "timestamp":    timestamp,
            })

    return {"date": date_str, "captures": results, "count": len(results)}


def _parse_capture_filename(stem: str) -> tuple[str, str]:
    """
    Parse '{person_id}_{YYYY-MM-DD}_{HH-MM-SS}_{mode}' stem.
    Returns (person_id, 'YYYY-MM-DD HH:MM:SS').
    Works even if person_id itself contains underscores.
    """
    # Find the date with regex
    m = re.search(r"(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})", stem)
    if m:
        date_part = m.group(1)
        time_part = m.group(2).replace("-", ":")
        timestamp = f"{date_part} {time_part}"
        # person_id is everything before the date match
        person_id = stem[: m.start()].rstrip("_")
    else:
        person_id = stem.split("_")[0]
        timestamp = ""
    return person_id, timestamp


@router.get("/captures/image")
def serve_capture_image(
    date:     str = Query(...),
    mode:     str = Query(...),
    filename: str = Query(...),
):
    """Serve a face capture image file directly."""
    # Sanitize inputs to prevent path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if mode not in ("checkin", "checkout"):
        raise HTTPException(status_code=400, detail="Invalid mode")
    try:
        _validate_date(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date")

    img_path = FACE_CAPTURES_DIR / date / mode / filename
    if not img_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(
        path=str(img_path),
        media_type="image/jpeg",
        filename=filename,
    )


def _validate_date(date_str: str):
    from datetime import datetime
    datetime.strptime(date_str, "%Y-%m-%d")
