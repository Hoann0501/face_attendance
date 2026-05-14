from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from typing import Optional

from backend.schemas import PersonCreate, PersonUpdate, PersonStatusPatch, PersonOut
from backend.services import person_service as svc
from backend.services.face_service import get_face_verifier
from backend.config import ENROLL_IMAGES_DIR

router = APIRouter(prefix="/people", tags=["people"])

_IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


# ── helpers ──────────────────────────────────────────────────────────────────

def _with_template(person: dict) -> dict:
    try:
        verifier = get_face_verifier()
        person["has_template"] = verifier.has_template(person["person_id"])
    except Exception:
        person["has_template"] = False
    return person


# ── list ─────────────────────────────────────────────────────────────────────

@router.get("")
def list_people():
    people = svc.get_all_people()

    # Enrich with last attendance info (scan last 30 days)
    try:
        from backend.services.attendance_service import get_recent_attendance_summary
        att_summary = get_recent_attendance_summary(days=30)
    except Exception:
        att_summary = {}

    result = []
    for p in people:
        _with_template(p)
        att = att_summary.get(p["person_id"], {})
        p["last_check_in"]  = att.get("last_check_in",  "")
        p["last_check_out"] = att.get("last_check_out", "")
        p["last_att_date"]  = att.get("last_date",      "")
        result.append(p)

    return result


# ── person detail ─────────────────────────────────────────────────────────────

@router.get("/{person_id}/attendance")
def person_attendance(
    person_id: str,
    days: int = Query(default=7, ge=0),
):
    """Attendance history for one person. days=0 means all records."""
    from backend.services.attendance_service import get_person_attendance_history
    records = get_person_attendance_history(person_id, days=days)
    return {"person_id": person_id, "days": days, "records": records, "count": len(records)}


@router.get("/{person_id}/enroll-images")
def list_enroll_images(person_id: str):
    """List enroll images for a person."""
    enroll_dir = ENROLL_IMAGES_DIR / person_id
    images = []
    if enroll_dir.exists():
        for f in sorted(enroll_dir.iterdir()):
            if f.suffix.lower() in _IMG_EXTS:
                images.append({
                    "filename": f.name,
                    "url": f"/people/{person_id}/enroll-images/{f.name}",
                })
    return {"person_id": person_id, "images": images, "count": len(images)}


@router.get("/{person_id}/enroll-images/{filename}")
def serve_enroll_image(person_id: str, filename: str):
    """Serve a single enroll image file."""
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    img_path = ENROLL_IMAGES_DIR / person_id / filename
    if not img_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(str(img_path), media_type="image/jpeg")


@router.get("/{person_id}")
def get_person(person_id: str):
    person = svc.get_person(person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    return _with_template(person)


# ── CRUD ─────────────────────────────────────────────────────────────────────

@router.post("", status_code=201)
def create_person(body: PersonCreate):
    existing = svc.get_person(body.person_id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Person {body.person_id} already exists")
    person = svc.create_person(
        person_id=body.person_id,
        full_name=body.full_name,
        student_code=body.student_code,
        class_name=body.class_name,
        status=body.status,
    )
    return _with_template(person)


@router.put("/{person_id}")
def update_person(person_id: str, body: PersonUpdate):
    existing = svc.get_person(person_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Person not found")
    person = svc.update_person(
        person_id,
        full_name=body.full_name,
        student_code=body.student_code,
        class_name=body.class_name,
        status=body.status,
    )
    return _with_template(person)


@router.patch("/{person_id}/status")
def patch_status(person_id: str, body: PersonStatusPatch):
    existing = svc.get_person(person_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Person not found")
    if body.status not in ("active", "inactive"):
        raise HTTPException(status_code=400, detail="status must be 'active' or 'inactive'")
    person = svc.patch_person_status(person_id, body.status)
    return _with_template(person)


@router.delete("/{person_id}")
def delete_person(person_id: str):
    existing = svc.get_person(person_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Person not found")

    svc.delete_person(person_id)

    try:
        verifier = get_face_verifier()
        verifier.delete_person_template(person_id)
    except Exception:
        pass

    return {"message": f"Deleted {person_id}"}
