from fastapi import APIRouter
from datetime import datetime, timezone, timedelta

router = APIRouter()


@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone(timedelta(hours=7))).isoformat(),
        "service": "Face Attendance Deploy",
    }
