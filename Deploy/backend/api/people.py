from fastapi import APIRouter, HTTPException, Path as FPath
from backend.schemas import PersonCreate, PersonUpdate, PersonStatusPatch, PersonOut
from backend.services import person_service as svc
from backend.services.face_service import get_face_verifier

router = APIRouter(prefix="/people", tags=["people"])


def _with_template(person: dict) -> dict:
    try:
        verifier = get_face_verifier()
        person["has_template"] = verifier.has_template(person["person_id"])
    except Exception:
        person["has_template"] = False
    return person


@router.get("", response_model=list[PersonOut])
def list_people():
    people = svc.get_all_people()
    return [_with_template(p) for p in people]


@router.get("/{person_id}", response_model=PersonOut)
def get_person(person_id: str):
    person = svc.get_person(person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    return _with_template(person)


@router.post("", response_model=PersonOut, status_code=201)
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


@router.put("/{person_id}", response_model=PersonOut)
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


@router.patch("/{person_id}/status", response_model=PersonOut)
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
