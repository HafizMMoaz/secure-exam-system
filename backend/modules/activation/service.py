import hashlib
import secrets
import string
from datetime import timedelta

import requests
from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import PyMongoError

from config.config import activation_codes_col, exams_col, BASE_URL, now
from enums.exam_state import ExamState
from enums.log_level import LogLevel
from enums.module_name import ModuleName
from exceptions import (
    ActivationCodeAlreadyUsedException,
    BadRequestException,
    DatabaseException,
    ExamNotFoundException,
    NotFoundException,
)


def _iso_dt(value):
    if value is None:
        return None
    return value.replace(microsecond=0).isoformat() + "Z"


def _validate_exam_id(exam_id):
    if not exam_id:
        raise BadRequestException("exam_id is required")
    return str(exam_id).strip()


def _validate_code(code):
    if not code:
        raise BadRequestException("code is required")
    return str(code).strip()


def _generate_code():
    return "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))


def _code_hash(code):
    return hashlib.sha256(code.encode()).hexdigest()


def _send_log(level, action, exam_id, details=None, user_id=None):
    payload = {
        "module": ModuleName.ACTIVATION.value,
        "level": level,
        "user_id": user_id or "",
        "exam_id": exam_id or "",
        "action": action,
        "details": details or {},
        "timestamp": now().replace(microsecond=0).isoformat() + "Z",
    }
    try:
        requests.post(f"{BASE_URL}/api/logs/write", json=payload, timeout=2)
    except Exception:
        pass


def generate_activation_code(user_context, payload):
    exam_id = _validate_exam_id((payload or {}).get("exam_id"))

    try:
        exam = exams_col.find_one({"_id": ObjectId(exam_id)})
    except (InvalidId, TypeError):
        raise ExamNotFoundException()
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    if not exam:
        raise ExamNotFoundException()

    if exam.get("state") != ExamState.TEACHER_APPROVED.value:
        raise BadRequestException("Exam must be in TEACHER_APPROVED state")

    code = _generate_code()
    code_hash = _code_hash(code)
    current = now()

    doc = {
        "exam_id": exam_id,
        "code_hash": code_hash,
        "created_by": (user_context or {}).get("user_id"),
        "created_at": current,
        "expires_at": current + timedelta(minutes=10),
        "is_used": False,
        "used_by": None,
        "used_at": None,
    }

    try:
        activation_codes_col.insert_one(doc)
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    _send_log(
        LogLevel.INFO.value,
        "activation_code_generated",
        exam_id,
        {"exam_id": exam_id},
        (user_context or {}).get("user_id"),
    )

    return {
        "code": code,
        "exam_id": exam_id,
        "expires_in_minutes": 10,
    }


def validate_activation_code(user_context, payload):
    exam_id = _validate_exam_id((payload or {}).get("exam_id"))
    code = _validate_code((payload or {}).get("code"))
    code_hash = _code_hash(code)

    try:
        activation = activation_codes_col.find_one({"exam_id": exam_id, "code_hash": code_hash})
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    if not activation:
        _send_log(
            LogLevel.SECURITY.value,
            "invalid_activation_code",
            exam_id,
            {"exam_id": exam_id},
            (user_context or {}).get("user_id"),
        )
        raise BadRequestException("Invalid activation code")

    if activation.get("is_used"):
        raise ActivationCodeAlreadyUsedException()

    expires_at = activation.get("expires_at")
    if expires_at and expires_at < now():
        _send_log(
            LogLevel.WARNING.value,
            "expired_activation_code",
            exam_id,
            {"exam_id": exam_id},
            (user_context or {}).get("user_id"),
        )
        raise BadRequestException("Activation code has expired")

    try:
        activation_codes_col.update_one(
            {"_id": activation.get("_id")},
            {
                "$set": {
                    "is_used": True,
                    "used_by": (user_context or {}).get("user_id"),
                    "used_at": now(),
                }
            },
        )

        exams_col.update_one(
            {"_id": ObjectId(exam_id)},
            {"$set": {"state": ExamState.ACTIVATION_VALID.value}},
        )
    except (InvalidId, TypeError):
        raise ExamNotFoundException()
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    _send_log(
        LogLevel.INFO.value,
        "activation_code_validated",
        exam_id,
        {"exam_id": exam_id, "student_id": (user_context or {}).get("user_id")},
        (user_context or {}).get("user_id"),
    )

    return {"exam_id": exam_id, "state": ExamState.ACTIVATION_VALID.value}


def get_activation_status(exam_id):
    exam_id = _validate_exam_id(exam_id)

    try:
        activation = activation_codes_col.find({"exam_id": exam_id}).sort("created_at", -1).limit(1)
        latest = next(activation, None)
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    if not latest:
        raise NotFoundException("No activation code found for this exam")

    expires_at = latest.get("expires_at")
    created_at = latest.get("created_at")
    used_at = latest.get("used_at")

    return {
        "exam_id": exam_id,
        "is_used": bool(latest.get("is_used", False)),
        "used_by": latest.get("used_by"),
        "used_at": _iso_dt(used_at),
        "created_at": _iso_dt(created_at),
        "expires_at": _iso_dt(expires_at),
        "is_expired": bool(expires_at and expires_at < now()),
    }


def get_health():
    return {
        "module_name": ModuleName.ACTIVATION.value,
        "dependencies": ["mongodb"],
        "version": "1.0.0",
        "healthy": True,
    }
