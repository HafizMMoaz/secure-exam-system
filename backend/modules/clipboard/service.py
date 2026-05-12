import requests

from pymongo.errors import PyMongoError

from config.config import BASE_URL, now, clipboard_events_col
from enums.log_level import LogLevel
from enums.module_name import ModuleName
from enums.risk_metric import RiskMetric
from exceptions import BadRequestException, DatabaseException, ForbiddenException


ALLOWED_EVENT_TYPES = {"copy", "cut", "paste"}


def _iso(dt):
    if dt is None:
        return None
    return dt.isoformat()


def _send_log(level, user_id, action, details):
    payload = {
        "module": ModuleName.CLIPBOARD.value,
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
    content_length = (payload or {}).get("content_length", 0)

    missing = [field for field in ("exam_id", "event_type", "timestamp") if not (payload or {}).get(field)]
    if missing:
        raise BadRequestException(f"Missing required fields: {', '.join(missing)}")

    if not isinstance(event_type, str):
        raise BadRequestException("event_type must be a string")

    event_type = event_type.lower()
    if event_type not in ALLOWED_EVENT_TYPES:
        raise BadRequestException("event_type must be one of copy, cut, paste")

    if content_length is None:
        content_length = 0

    try:
        content_length = int(content_length)
    except (TypeError, ValueError):
        raise BadRequestException("content_length must be an integer")

    if content_length < 0:
        raise BadRequestException("content_length must be greater than or equal to 0")

    user_id = (user_context or {}).get("user_id")

    doc = {
        "exam_id": exam_id,
        "student_id": user_id,
        "event_type": event_type,
        "content_length": content_length,
        "client_timestamp": timestamp,
        "server_timestamp": now(),
    }

    try:
        clipboard_events_col.insert_one(doc)
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    # §24 bonus: push to WebSocket subscribers of this exam's room.
    from middleware.socketio_app import emit_monitoring_event
    emit_monitoring_event(exam_id, "clipboard_event", {
        "user_id": user_id, "exam_id": exam_id,
        "event_type": event_type, "content_length": content_length,
        "timestamp": now().isoformat(),
    })

    if event_type == "paste":
        _send_log(LogLevel.SECURITY.value, user_id, "clipboard_paste_detected", {"exam_id": exam_id, "event_type": event_type, "content_length": content_length})
    elif event_type == "copy":
        _send_log(LogLevel.WARNING.value, user_id, "clipboard_copy_detected", {"exam_id": exam_id, "event_type": event_type, "content_length": content_length})
    else:
        _send_log(LogLevel.WARNING.value, user_id, "clipboard_cut_detected", {"exam_id": exam_id, "event_type": event_type, "content_length": content_length})

    return {"recorded": True, "event_type": event_type}


def get_summary(user_context, exam_id, requested_user_id=None):
    if not exam_id:
        raise BadRequestException("exam_id is required")

    current_user = user_context or {}
    if requested_user_id and current_user.get("role") == "student" and requested_user_id != current_user.get("user_id"):
        raise ForbiddenException("Students cannot access other users' clipboard data")

    student_id = requested_user_id or current_user.get("user_id")
    if not student_id:
        raise BadRequestException("student_id could not be determined")

    try:
        cursor = list(clipboard_events_col.find({"exam_id": exam_id, "student_id": student_id}).sort("server_timestamp", 1))
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    copy_count = 0
    cut_count = 0
    paste_count = 0
    suspicious_paste_count = 0
    events = []

    for event in cursor:
        event_type = event.get("event_type")
        content_length = event.get("content_length", 0)
        if event_type == "copy":
            copy_count += 1
        elif event_type == "cut":
            cut_count += 1
        elif event_type == "paste":
            paste_count += 1
            if content_length > 100:
                suspicious_paste_count += 1

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
        "copy_count": copy_count,
        "cut_count": cut_count,
        "paste_count": paste_count,
        "total_events": len(cursor),
        "suspicious_paste_count": suspicious_paste_count,
        "events": events,
    }


def get_risk_data(user_id, exam_id):
    if not user_id:
        raise BadRequestException("user_id is required")
    if not exam_id:
        raise BadRequestException("exam_id is required")

    try:
        paste_count = clipboard_events_col.count_documents(
            {"exam_id": exam_id, "student_id": user_id, "event_type": "paste"}
        )
        copy_count = clipboard_events_col.count_documents(
            {"exam_id": exam_id, "student_id": user_id, "event_type": "copy"}
        )
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    timestamp = now().isoformat()
    return [
        {
            "user_id": user_id,
            "exam_id": exam_id,
            "timestamp": timestamp,
            "metric": RiskMetric.CLIPBOARD_PASTE_COUNT.value,
            "value": paste_count,
        },
        {
            "user_id": user_id,
            "exam_id": exam_id,
            "timestamp": timestamp,
            "metric": RiskMetric.CLIPBOARD_COPY_COUNT.value,
            "value": copy_count,
        },
    ]


def get_health():
    return {"module_name": ModuleName.CLIPBOARD.value, "dependencies": ["mongodb"], "version": "1.0.0", "healthy": True}
