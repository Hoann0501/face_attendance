from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from typing import List, Optional

from backend.schemas import (
    FaceRegisterResponse, FaceSearchResponse, FaceVerifyResponse, FaceAnalysisResponse
)
from backend.services import face_service as svc

router = APIRouter(prefix="/face", tags=["face"])


@router.post("/register", response_model=FaceRegisterResponse)
async def register_face(
    person_id: str = Form(...),
    full_name: str = Form(default=""),
    student_code: str = Form(default=""),
    class_name: str = Form(default=""),
    images: List[UploadFile] = File(...),
):
    if not person_id.strip():
        raise HTTPException(status_code=400, detail="person_id không được rỗng")

    image_bytes_list = [await img.read() for img in images]

    result = svc.register_face(
        person_id=person_id.strip(),
        image_bytes_list=image_bytes_list,
        full_name=full_name,
        student_code=student_code,
        class_name=class_name,
    )

    if not result["ok"]:
        raise HTTPException(status_code=422, detail=result["message"])

    # Reload templates so subsequent requests use updated data
    svc.reload_templates()

    return FaceRegisterResponse(
        person_id=person_id,
        num_images_processed=result["num_images_processed"],
        num_embeddings_created=result["num_embeddings_created"],
        template_updated=result["template_updated"],
        person_upserted=result["person_upserted"],
        message=result["message"],
    )


@router.post("/search")
async def search_face(
    image: UploadFile = File(...),
    top_k: int = Query(default=5, ge=1, le=20),
):
    image_bytes = await image.read()
    result = svc.search_face(image_bytes, top_k=top_k)

    if not result["ok"]:
        raise HTTPException(status_code=422, detail=result.get("message", "Search failed"))

    return result


@router.post("/verify")
async def verify_face(
    person_id: str = Form(...),
    image: UploadFile = File(...),
):
    image_bytes = await image.read()
    result = svc.verify_face(person_id, image_bytes)

    if not result["ok"]:
        raise HTTPException(status_code=422, detail=result.get("message", "Verify failed"))

    return result


@router.post("/analyze")
async def analyze_faces(image: UploadFile = File(...)):
    image_bytes = await image.read()
    result = svc.analyze_faces(image_bytes)

    if not result["ok"]:
        raise HTTPException(status_code=422, detail=result.get("message", "Analyze failed"))

    return result
