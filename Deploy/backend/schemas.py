"""
Pydantic schemas for request / response validation.
"""

from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------

class PersonCreate(BaseModel):
    person_id: str
    full_name: str = ""
    student_code: str = ""
    class_name: str = ""
    status: str = "active"


class PersonUpdate(BaseModel):
    full_name: Optional[str] = None
    student_code: Optional[str] = None
    class_name: Optional[str] = None
    status: Optional[str] = None


class PersonStatusPatch(BaseModel):
    status: str


class PersonOut(BaseModel):
    person_id: str
    full_name: str
    student_code: str
    class_name: str
    status: str
    created_at: str
    updated_at: str
    has_template: bool = False


# ---------------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------------

class AttendanceCheckIn(BaseModel):
    person_id: str
    similarity: float = 0.0
    liveness_status: str = "REAL_ATTENDANCE_OK"
    face_real_score: float = 0.0
    full_real_score: float = 0.0


class AttendanceCheckOut(BaseModel):
    person_id: str
    similarity: float = 0.0
    liveness_status: str = "REAL_ATTENDANCE_OK"
    face_real_score: float = 0.0
    full_real_score: float = 0.0


class AttendanceRecord(BaseModel):
    id: int
    person_id: str
    full_name: str = ""
    student_code: str = ""
    class_name: str = ""
    date: str
    check_in_time: Optional[str] = None
    check_out_time: Optional[str] = None
    check_in_similarity: Optional[float] = None
    check_out_similarity: Optional[float] = None
    check_in_liveness_status: Optional[str] = None
    check_out_liveness_status: Optional[str] = None
    face_real_score: Optional[float] = None
    full_real_score: Optional[float] = None
    status: str
    created_at: str
    updated_at: str


class AttendanceEvent(BaseModel):
    """Lightweight event for realtime feed."""
    id: int
    person_id: str
    full_name: str = ""
    student_code: str = ""
    event_type: str  # CHECK_IN | CHECK_OUT
    event_time: str
    similarity: float = 0.0
    liveness_status: str = ""
    status: str = ""


# ---------------------------------------------------------------------------
# Face
# ---------------------------------------------------------------------------

class FaceSearchResult(BaseModel):
    person_id: str
    full_name: str = ""
    student_code: str = ""
    class_name: str = ""
    status: str = ""
    similarity: float


class FaceSearchResponse(BaseModel):
    num_faces_detected: int
    results: List[FaceSearchResult]


class FaceVerifyResponse(BaseModel):
    person_id: str
    is_verified: bool
    similarity: float
    threshold: float
    reason: str = ""


class FaceRegisterRequest(BaseModel):
    person_id: str
    full_name: str = ""
    student_code: str = ""
    class_name: str = ""


class FaceRegisterResponse(BaseModel):
    person_id: str
    num_images_processed: int
    num_embeddings_created: int
    template_updated: bool
    person_upserted: bool
    message: str


class FaceAnalysisResult(BaseModel):
    face_id: int
    det_score: float
    bbox: List[float]
    landmarks: Optional[List] = None
    embedding_dim: Optional[int] = None
    gender: Optional[str] = None
    gender_conf: Optional[float] = None
    age: Optional[float] = None
    age_group: Optional[str] = None
    age_group_conf: Optional[float] = None


class FaceAnalysisResponse(BaseModel):
    num_faces: int
    faces: List[FaceAnalysisResult]
