import requests

from pymongo.errors import PyMongoError

from config.config import BASE_URL, now, tab_events_col
from enums.log_level import LogLevel
from enums.module_name import ModuleName
from enums.risk_metric import RiskMetric
from exceptions import BadRequestException, DatabaseException, ForbiddenException


ALLOWED_EVENT_TYPES = {"blur", "focus", "hidden", "visible"}


def _iso(dt):
    if dt is None:
        return None
    return dt.isoformat()


def _send_log(level, user_id, action, details):
    payload = {
        "module": ModuleName.TAB.value,
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


def record_event(user_context, payload):
    exam_id = (payload or {}).get("exam_id")
    event_type = (payload or {}).get("event_type")
    timestamp = (payload or {}).get("timestamp")

    missing = [field for field in ("exam_id", "event_type", "timestamp") if not (payload or {}).get(field)]
    if missing:
        raise BadRequestException(f"Missing required fields: {', '.join(missing)}")

    if not isinstance(event_type, str):
        raise BadRequestException("event_type must be a string")

    event_type = event_type.lower()
    if event_type not in ALLOWED_EVENT_TYPES:
        raise BadRequestException("event_type must be one of blur, focus, hidden, visible")

    user_id = (user_context or {}).get("user_id")

    doc = {
        "exam_id": exam_id,
        "student_id": user_id,
        "event_type": event_type,
        "client_timestamp": timestamp,
        "server_timestamp": now(),
    }

    try:
        tab_events_col.insert_one(doc)
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    if event_type in {"blur", "hidden"}:
        _send_log(LogLevel.SECURITY.value, user_id, "tab_switch_detected", {"exam_id": exam_id, "event_type": event_type})
    else:
        _send_log(LogLevel.INFO.value, user_id, "tab_focus_returned", {"exam_id": exam_id, "event_type": event_type})

    return {"recorded": True, "event_type": event_type}


def get_summary(user_context, exam_id, requested_user_id=None):
    if not exam_id:
        raise BadRequestException("exam_id is required")

    current_user = user_context or {}
    current_role = current_user.get("role")
    if requested_user_id and current_role == "student":
        raise ForbiddenException("Students cannot access other users' tab data")

    student_id = requested_user_id or current_user.get("user_id")
    if not student_id:
        raise BadRequestException("student_id could not be determined")

    try:
        cursor = list(tab_events_col.find({"exam_id": exam_id, "student_id": student_id}).sort("server_timestamp", 1))
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    switch_events = 0
    focus_return_events = 0
    events = []

    for event in cursor:
        event_type = event.get("event_type")
        if event_type in {"blur", "hidden"}:
            switch_events += 1
        elif event_type in {"focus", "visible"}:
            focus_return_events += 1

        events.append(
            {
                "event_type": event_type,
                "client_timestamp": event.get("client_timestamp"),
                "server_timestamp": _iso(event.get("server_timestamp")),
            }
        )

    return {
        "exam_id": exam_id,
        "student_id": student_id,
        "tab_switch_count": switch_events,
        "focus_return_count": focus_return_events,
        "events": events,
    }


def get_risk_data(user_id, exam_id):
    if not user_id:
        raise BadRequestException("user_id is required")
    if not exam_id:
        raise BadRequestException("exam_id is required")

    try:
        count = tab_events_col.count_documents(
            {
                "exam_id": exam_id,
                "student_id": user_id,
                "event_type": {"$in": ["blur", "hidden"]},
            }
        )
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    return [
        {
            "user_id": user_id,
            "exam_id": exam_id,
            "timestamp": now().isoformat(),
            "metric": RiskMetric.TAB_SWITCH_COUNT.value,
            "value": count,
        }
    ]


def get_health():
    return {"module_name": ModuleName.TAB.value, "dependencies": ["mongodb"], "version": "1.0.0", "healthy": True}
