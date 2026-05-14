import requests

from pymongo.errors import PyMongoError

from config.config import BASE_URL, now, activity_events_col
from enums.log_level import LogLevel
from enums.module_name import ModuleName
from enums.risk_metric import RiskMetric
from exceptions import BadRequestException, DatabaseException, ForbiddenException


ALLOWED_ACTIVITY_EVENTS = {
    "question_viewed",
    "answer_selected",
    "answer_changed",
    "exam_started",
    "exam_submitted",
    "page_scroll",
}


def _iso(dt):
    if dt is None:
        return None
    return dt.isoformat()


def _send_log(level, user_id, action, details):
    payload = {
        "module": ModuleName.ACTIVITY.value,
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


def record_heartbeat(user_context, payload):
    exam_id = (payload or {}).get("exam_id")
    timestamp = (payload or {}).get("timestamp")

    missing = [field for field in ("exam_id", "timestamp") if not (payload or {}).get(field)]
    if missing:
        raise BadRequestException(f"Missing required fields: {', '.join(missing)}")

    user_id = (user_context or {}).get("user_id")

    try:
        previous = activity_events_col.find_one(
            {"exam_id": exam_id, "student_id": user_id, "event_type": "heartbeat"},
            sort=[("server_timestamp", -1)],
        )
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    if previous:
        idle_seconds = (now() - previous["server_timestamp"]).total_seconds()
    else:
        idle_seconds = 0

    is_idle = idle_seconds > 60

    doc = {
        "exam_id": exam_id,
        "student_id": user_id,
        "event_type": "heartbeat",
        "client_timestamp": timestamp,
        "server_timestamp": now(),
        "idle_seconds": int(idle_seconds),
        "is_idle": is_idle,
    }

    try:
        activity_events_col.insert_one(doc)
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    # section 24 bonus: push to WebSocket subscribers of this exam's room.
    from middleware.socketio_app import emit_monitoring_event
    emit_monitoring_event(exam_id, "activity_event", {
        "user_id": user_id, "exam_id": exam_id,
        "event_type": "heartbeat", "idle_seconds": int(idle_seconds),
        "is_idle": is_idle, "timestamp": now().isoformat(),
    })

    if is_idle:
        _send_log(LogLevel.WARNING.value, user_id, "idle_period_detected", {"exam_id": exam_id, "idle_seconds": int(idle_seconds)})

    return {"recorded": True, "idle_seconds": int(idle_seconds), "is_idle": is_idle}


def record_event(user_context, payload):
    exam_id = (payload or {}).get("exam_id")
    event_type = (payload or {}).get("event_type")
    details = (payload or {}).get("details", {})
    timestamp = (payload or {}).get("timestamp")

    missing = [field for field in ("exam_id", "event_type", "timestamp") if not (payload or {}).get(field)]
    if missing:
        raise BadRequestException(f"Missing required fields: {', '.join(missing)}")

    if event_type not in ALLOWED_ACTIVITY_EVENTS:
        raise BadRequestException("event_type must be one of question_viewed, answer_selected, answer_changed, exam_started, exam_submitted, page_scroll")

    if details is None:
        details = {}
    if not isinstance(details, dict):
        raise BadRequestException("details must be an object")

    user_id = (user_context or {}).get("user_id")

    doc = {
        "exam_id": exam_id,
        "student_id": user_id,
        "event_type": event_type,
        "details": details,
        "client_timestamp": timestamp,
        "server_timestamp": now(),
        "idle_seconds": 0,
        "is_idle": False,
    }

    try:
        activity_events_col.insert_one(doc)
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    _send_log(LogLevel.INFO.value, user_id, f"activity_{event_type}", {"exam_id": exam_id, "event_type": event_type})

    return {"recorded": True, "event_type": event_type}


def get_summary(user_context, exam_id, requested_user_id=None):
    if not exam_id:
        raise BadRequestException("exam_id is required")

    current_user = user_context or {}
    if requested_user_id and current_user.get("role") == "student":
        raise ForbiddenException("Students cannot access other users' activity data")

    student_id = requested_user_id or current_user.get("user_id")
    if not student_id:
        raise BadRequestException("student_id could not be determined")

    try:
        cursor = list(activity_events_col.find({"exam_id": exam_id, "student_id": student_id}).sort("server_timestamp", 1))
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    event_counts = {}
    total_idle_seconds = 0
    idle_period_count = 0

    for event in cursor:
        event_type = event.get("event_type")
        event_counts[event_type] = event_counts.get(event_type, 0) + 1
        if event.get("is_idle"):
            idle_period_count += 1
            total_idle_seconds += int(event.get("idle_seconds", 0))

    return {
        "exam_id": exam_id,
        "student_id": student_id,
        "total_idle_seconds": total_idle_seconds,
        "idle_period_count": idle_period_count,
        "event_counts": event_counts,
        "total_events": len(cursor),
    }


def get_risk_data(user_id, exam_id):
    if not user_id:
        raise BadRequestException("user_id is required")
    if not exam_id:
        raise BadRequestException("exam_id is required")

    try:
        total_idle_seconds = activity_events_col.aggregate(
            [
                {"$match": {"exam_id": exam_id, "student_id": user_id, "is_idle": True}},
                {"$group": {"_id": None, "total": {"$sum": "$idle_seconds"}}},
            ]
        )
        aggregation = list(total_idle_seconds)
        total = aggregation[0]["total"] if aggregation else 0
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    return [
        {
            "user_id": user_id,
            "exam_id": exam_id,
            "timestamp": now().isoformat(),
            "metric": RiskMetric.IDLE_TIME_SECONDS.value,
            "value": total,
        }
    ]


def get_health():
    return {"module_name": ModuleName.ACTIVITY.value, "dependencies": ["mongodb"], "version": "1.0.0", "healthy": True}
