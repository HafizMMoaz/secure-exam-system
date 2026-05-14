import requests
from datetime import timedelta
from bson import ObjectId
from pymongo.errors import PyMongoError
from pytz import utc

from config.config import exams_col, exam_sessions_col, BASE_URL, now
from middleware.state_client import transition_exam_state
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


def _exam_is_complete_by_quorum(exam_id):
    """
    Early-finalization rule (in addition to end_time):
      Only treat the exam as fully done if the enrollment cap has been
      reached (no more students can join) AND every approved student has
      submitted. Without the cap check, a single submitter would close
      an exam that still had seats - locking out late enrolees.

    If the cap isn't reached, the exam stays IN_PROGRESS and end_time
    becomes the only finalizer (via the auto_submit job).
    """
    try:
        exam = exams_col.find_one({"_id": ObjectId(exam_id)})
    except Exception:
        return False
    if not exam:
        return False

    max_students = int(exam.get("max_students", 0) or 0)
    students_count = int(exam.get("students_count", 0) or 0)
    if max_students <= 0 or students_count < max_students:
        return False

    approved_ids = [
        s.get("student_id")
        for s in (exam.get("students") or [])
        if s.get("approved") and s.get("student_id")
    ]
    if not approved_ids:
        return False
    submitted = exam_sessions_col.count_documents({
        "exam_id": str(exam_id),
        "student_id": {"$in": approved_ids},
        "submitted_at": {"$ne": None},
    })
    return submitted >= len(approved_ids)


def _finalize_exam(exam_id, auth_header):
    """
    Flip the exam to SUBMITTED and kick off risk compute. Idempotent -
    if the exam is already past SUBMITTED, the state writer treats the
    repeat as a no-op.
    """
    try:
        transition_exam_state(
            exam_id,
            ExamState.SUBMITTED.value,
            auth_header,
            ModuleName.TIMER.value,
        )
    except Exception:
        # Already past SUBMITTED - fine, fall through to risk compute.
        pass

    import threading

    def _auto_risk():
        try:
            from modules.risk.service import compute_exam_risk
            compute_exam_risk(
                user_context={"role": "system", "user_id": "system_timer"},
                exam_id=exam_id,
                auth_header=auth_header,
                system_actor=True,
            )
        except Exception as exc:
            _send_log(LogLevel.WARNING.value, "system", "auto_risk_failed",
                      {"exam_id": exam_id, "error": str(exc)})

    threading.Thread(target=_auto_risk, daemon=True).start()


def _iso(dt):
    if dt is None:
        return None
    normalized = _normalize_dt(dt)
    return normalized.astimezone(utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_dt(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return utc.localize(value)
    return value


def _send_log(level, user_id, action, details):
    payload = {
        "module": ModuleName.TIMER.value,
        "level": level,
        "user_id": user_id or "",
        "exam_id": details.get("exam_id") if details else "",
        "action": action,
        "details": details or {},
        "timestamp": now().astimezone(utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    try:
        requests.post(f"{BASE_URL}/api/logs/write", json=payload, timeout=2)
    except Exception:
        pass


def start_exam(user_context, payload, auth_header=""):
    exam_id = (payload or {}).get("exam_id")
    if not exam_id:
        raise BadRequestException("exam_id is required")

    try:
        exam = exams_col.find_one({"_id": ObjectId(exam_id)})
    except Exception:
        raise ExamNotFoundException()

    if not exam:
        raise ExamNotFoundException()

    if exam.get("state") not in {ExamState.ACTIVATION_VALID.value, ExamState.IN_PROGRESS.value}:
        raise ExamStateException(current_state=exam.get("state"), required_state=ExamState.ACTIVATION_VALID.value)

    current_time = now()
    start_time = _normalize_dt(exam.get("start_time"))
    end_time = _normalize_dt(exam.get("end_time"))

    if start_time and current_time < start_time:
        raise BadRequestException("Exam has not started yet")
    if end_time and current_time > end_time:
        raise BadRequestException("Exam period has ended")

    user_id = (user_context or {}).get("user_id")

    # Check for existing active session
    try:
        existing = exam_sessions_col.find_one({"exam_id": exam_id, "student_id": user_id, "is_active": True})
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    if existing:
        existing_end_time = _normalize_dt(existing.get("end_time"))
        remaining = int((existing_end_time - current_time).total_seconds()) if existing_end_time else 0
        return {
            "exam_id": exam_id,
            "start_time": _iso(existing.get("start_time")),
            "end_time": _iso(existing_end_time or existing.get("end_time")),
            "duration_minutes": existing.get("duration_minutes", int(exam.get("duration_minutes", 60))),
            "remaining_seconds": max(0, remaining),
            "resumed": True,
        }

    duration_minutes = int(exam.get("duration_minutes", 60))
    session_start_time = current_time
    session_end_time = session_start_time + timedelta(minutes=duration_minutes)

    session_doc = {
        "exam_id": exam_id,
        "student_id": user_id,
        "start_time": session_start_time,
        "end_time": session_end_time,
        "duration_minutes": duration_minutes,
        "is_active": True,
        "submitted_at": None,
    }

    try:
        exam_sessions_col.insert_one(session_doc)
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    # section 27.6 (strict): state transition routed through Module 1.
    transition_exam_state(
        exam_id,
        ExamState.IN_PROGRESS.value,
        auth_header,
        ModuleName.TIMER.value,
    )

    _send_log(LogLevel.INFO.value, user_id, "exam_started", {"exam_id": exam_id, "student_id": user_id, "duration_minutes": duration_minutes})

    remaining_seconds = int((session_end_time - current_time).total_seconds())

    return {
        "exam_id": exam_id,
        "start_time": _iso(session_start_time),
        "end_time": _iso(session_end_time),
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

    end_time = _normalize_dt(session.get("end_time"))
    remaining_seconds = int((end_time - now()).total_seconds()) if end_time else 0

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


def submit_exam(user_context, payload, auth_header=""):
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

    # Mongo stores datetimes naive; normalize to the configured TZ before
    # comparing with `now()` (which is TZ-aware).
    end_time = _normalize_dt(session.get("end_time"))
    if end_time and now() > end_time:
        raise ExamStateException("Exam time has expired")

    if session.get("submitted_at") is not None:
        raise ExamAlreadySubmittedException()

    try:
        exam_sessions_col.update_one({"_id": session.get("_id")}, {"$set": {"is_active": False, "submitted_at": now()}})
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    _send_log(LogLevel.INFO.value, user_id, "exam_submitted", {"exam_id": exam_id, "student_id": user_id})

    # IMPORTANT - the exam stays IN_PROGRESS unless the enrollment cap is
    # full AND every approved student has submitted. Otherwise end_time
    # is the only finalizer (via the auto_submit job). This stops a
    # single submitter from prematurely closing an exam that still has
    # open seats.
    try:
        if _exam_is_complete_by_quorum(exam_id):
            _finalize_exam(exam_id, auth_header)
    except Exception as exc:
        _send_log(LogLevel.WARNING.value, "system", "finalize_check_failed",
                  {"exam_id": exam_id, "error": str(exc)})

    return {"exam_id": exam_id, "submitted_at": _iso(now())}


def get_health():
    return {"module_name": ModuleName.TIMER.value, "dependencies": ["mongodb"], "version": "1.0.0", "healthy": True}
