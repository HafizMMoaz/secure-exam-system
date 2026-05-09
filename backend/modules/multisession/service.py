import requests

from pymongo.errors import PyMongoError

from config.config import sessions_col, multisession_attempts_col, BASE_URL, now
from enums.module_name import ModuleName
from enums.log_level import LogLevel
from enums.risk_metric import RiskMetric
from exceptions import BadRequestException, DatabaseException, ForbiddenException


def _iso(dt):
    if dt is None:
        return None
    return dt.isoformat()


def _send_log(level, user_id, action, details):
    payload = {
        "module": ModuleName.MULTISESSION.value,
        "level": level,
        "user_id": user_id or "",
        "exam_id": details.get("exam_id") if details else "",
        "action": action,
        "details": details or {},
        "timestamp": now().isoformat(),
    }
    try:
        requests.post(f"{BASE_URL}/api/logs/write", json=payload, timeout=2)
    except Exception:
        pass


def detect_multi_session(user_context):
    user_id = (user_context or {}).get("user_id")
    current_session_id = (user_context or {}).get("session_id")

    if not user_id or not current_session_id:
        raise BadRequestException("user_id and session_id are required")

    try:
        conflicting_sessions = list(
            sessions_col.find(
                {
                    "user_id": user_id,
                    "is_active": True,
                    "session_id": {"$ne": current_session_id},
                }
            )
        )
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    conflicting_ids = [session.get("session_id") for session in conflicting_sessions if session.get("session_id")]

    if conflicting_ids:
        try:
            sessions_col.update_many(
                {
                    "user_id": user_id,
                    "is_active": True,
                    "session_id": {"$ne": current_session_id},
                },
                {"$set": {"is_active": False, "invalidated_at": now()}},
            )
            multisession_attempts_col.insert_one(
                {
                    "user_id": user_id,
                    "current_session_id": current_session_id,
                    "conflicting_session_ids": conflicting_ids,
                    "detected_at": now(),
                    "exam_id": "",
                }
            )
        except PyMongoError as exc:
            raise DatabaseException(str(exc))

        _send_log(
            LogLevel.SECURITY.value,
            user_id,
            "multi_session_detected",
            {
                "user_id": user_id,
                "conflicting_count": len(conflicting_ids),
                "invalidated_sessions": conflicting_ids,
            },
        )

        return {
            "multi_session_detected": True,
            "conflicting_sessions_found": len(conflicting_ids),
            "sessions_invalidated": len(conflicting_ids),
            "message": "Conflicting sessions have been invalidated",
        }

    return {
        "multi_session_detected": False,
        "conflicting_sessions_found": 0,
        "sessions_invalidated": 0,
        "message": "No conflicting sessions detected",
    }


def get_history(user_context, requested_user_id=None):
    current_user = user_context or {}
    if requested_user_id and current_user.get("role") == "student":
        raise ForbiddenException("Students cannot access other users' multisession history")

    user_id = requested_user_id or current_user.get("user_id")
    if not user_id:
        raise BadRequestException("user_id is required")

    try:
        cursor = list(multisession_attempts_col.find({"user_id": user_id}).sort("detected_at", -1))
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    attempts = []
    for attempt in cursor:
        attempts.append(
            {
                "attempt_id": str(attempt.get("_id")),
                "current_session_id": attempt.get("current_session_id"),
                "conflicting_session_ids": attempt.get("conflicting_session_ids", []),
                "detected_at": _iso(attempt.get("detected_at")),
                "exam_id": attempt.get("exam_id", ""),
            }
        )

    return {"user_id": user_id, "attempt_count": len(attempts), "attempts": attempts}


def get_risk_data(user_id, exam_id):
    if not user_id:
        raise BadRequestException("user_id is required")
    if not exam_id:
        raise BadRequestException("exam_id is required")

    try:
        attempt_count = multisession_attempts_col.count_documents({"user_id": user_id})
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    return [
        {
            "user_id": user_id,
            "exam_id": exam_id,
            "timestamp": now().isoformat(),
            "metric": RiskMetric.MULTI_SESSION_ATTEMPTS.value,
            "value": attempt_count,
        }
    ]


def get_health():
    return {"module_name": ModuleName.MULTISESSION.value, "dependencies": ["mongodb"], "version": "1.0.0", "healthy": True}
