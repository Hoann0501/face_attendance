import io
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import date
import pandas as pd

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
    """Delete attendance record for a specific person on a given date."""
    date_str = date or svc._today_str()
    try:
        _validate_date(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")

    import pandas as pd
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

    tmp = path.with_suffix(".tmp")
    df.to_csv(tmp, index=False, encoding="utf-8-sig")
    tmp.replace(path)

    return {"ok": True, "message": f"Deleted attendance for {person_id} on {date_str}"}


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


def _validate_date(date_str: str):
    from datetime import datetime
    datetime.strptime(date_str, "%Y-%m-%d")
