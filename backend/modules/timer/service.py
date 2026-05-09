import requests
from datetime import timedelta
from bson import ObjectId
from pymongo.errors import PyMongoError

from config.config import exams_col, exam_sessions_col, BASE_URL, now
from enums.module_name import ModuleName
from enums.log_level import LogLevel
from enums.exam_state import ExamState
from exceptions import (
    BadRequestException,
    DatabaseException,
    ExamNotFoundException,
    ExamStateException,
    ConflictException,
    ExamAlreadySubmittedException,
)


def _iso(dt):
    if dt is None:
        return None
    return dt.replace(microsecond=0).isoformat() + "Z"


def _send_log(level, user_id, action, details):
    payload = {
        "module": ModuleName.TIMER.value,
        "level": level,
        "user_id": user_id or "",
        "exam_id": details.get("exam_id") if details else "",
        "action": action,
        "details": details or {},
        "timestamp": now().replace(microsecond=0).isoformat() + "Z",
    }
    try:
        requests.post(f"{BASE_URL}/api/logs/write", json=payload, timeout=2)
    except Exception:
        pass


def start_exam(user_context, payload):
    exam_id = (payload or {}).get("exam_id")
    if not exam_id:
        raise BadRequestException("exam_id is required")

    try:
        exam = exams_col.find_one({"_id": ObjectId(exam_id)})
    except Exception:
        raise ExamNotFoundException()

    if not exam:
        raise ExamNotFoundException()

    if exam.get("state") != ExamState.ACTIVATION_VALID.value:
        raise ExamStateException(current_state=exam.get("state"), required_state=ExamState.ACTIVATION_VALID.value)

    user_id = (user_context or {}).get("user_id")

    # Check for existing active session
    try:
        existing = exam_sessions_col.find_one({"exam_id": exam_id, "student_id": user_id, "is_active": True})
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    if existing:
        raise ConflictException("Exam already started for this student")

    duration_minutes = int(exam.get("duration_minutes", 60))
    start_time = now()
    end_time = start_time + timedelta(minutes=duration_minutes)

    session_doc = {
        "exam_id": exam_id,
        "student_id": user_id,
        "start_time": start_time,
        "end_time": end_time,
        "duration_minutes": duration_minutes,
        "is_active": True,
        "submitted_at": None,
    }

    try:
        exam_sessions_col.insert_one(session_doc)
        exams_col.update_one({"_id": ObjectId(exam_id)}, {"$set": {"state": ExamState.IN_PROGRESS.value}})
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    _send_log(LogLevel.INFO.value, user_id, "exam_started", {"exam_id": exam_id, "student_id": user_id, "duration_minutes": duration_minutes})

    remaining_seconds = int((end_time - now()).total_seconds())

    return {
        "exam_id": exam_id,
        "start_time": _iso(start_time),
        "end_time": _iso(end_time),
        "duration_minutes": duration_minutes,
        "remaining_seconds": remaining_seconds if remaining_seconds > 0 else 0,
    }


def status(user_context, exam_id):
    if not exam_id:
        raise BadRequestException("exam_id is required")

    user_id = (user_context or {}).get("user_id")

    try:
        session = exam_sessions_col.find_one({"exam_id": exam_id, "student_id": user_id})
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    if not session:
        raise ExamStateException("Exam not started")

    end_time = session.get("end_time")
    remaining_seconds = int((end_time - now()).total_seconds())

    if remaining_seconds <= 0:
        # expire the session if still active
        if session.get("is_active"):
            try:
                exam_sessions_col.update_one({"_id": session.get("_id")}, {"$set": {"is_active": False, "submitted_at": now()}})
            except PyMongoError:
                pass
            _send_log(LogLevel.WARNING.value, user_id, "exam_time_expired", {"exam_id": exam_id, "student_id": user_id})
        return {"exam_id": exam_id, "remaining_seconds": 0, "time_expired": True}

    return {
        "exam_id": exam_id,
        "start_time": _iso(session.get("start_time")),
        "end_time": _iso(end_time),
        "remaining_seconds": remaining_seconds,
        "time_expired": False,
    }


def submit_exam(user_context, payload):
    exam_id = (payload or {}).get("exam_id")
    if not exam_id:
        raise BadRequestException("exam_id is required")

    user_id = (user_context or {}).get("user_id")

    try:
        session = exam_sessions_col.find_one({"exam_id": exam_id, "student_id": user_id})
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    if not session:
        raise ExamStateException("Exam not started")

    end_time = session.get("end_time")
    if now() > end_time:
        raise ExamStateException("Exam time has expired")

    if session.get("submitted_at") is not None:
        raise ExamAlreadySubmittedException()

    try:
        exam_sessions_col.update_one({"_id": session.get("_id")}, {"$set": {"is_active": False, "submitted_at": now()}})
        exams_col.update_one({"_id": ObjectId(exam_id)}, {"$set": {"state": ExamState.SUBMITTED.value}})
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    _send_log(LogLevel.INFO.value, user_id, "exam_submitted", {"exam_id": exam_id, "student_id": user_id})

    return {"exam_id": exam_id, "submitted_at": _iso(now())}


def get_health():
    return {"module_name": ModuleName.TIMER.value, "dependencies": ["mongodb"], "version": "1.0.0", "healthy": True}
