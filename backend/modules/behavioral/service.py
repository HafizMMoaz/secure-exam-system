import requests
from bson import ObjectId
from pymongo.errors import PyMongoError

from config.config import behavioral_events_col, clipboard_events_col, exams_col, BASE_URL, now
from enums.module_name import ModuleName
from enums.log_level import LogLevel
from enums.risk_metric import RiskMetric
from exceptions import BadRequestException, DatabaseException, ForbiddenException
from modules.behavioral.analyzer import is_fast_answer, analyze_behavior


def _iso(dt):
    if dt is None:
        return None
    return dt.isoformat()


def _send_log(level, user_id, action, details):
    payload = {
        "module": ModuleName.BEHAVIORAL.value,
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
    question_id = (payload or {}).get("question_id")
    answer_time_seconds = (payload or {}).get("answer_time_seconds")
    submission_time_seconds = (payload or {}).get("submission_time_seconds")
    edit_count = (payload or {}).get("edit_count", 0)
    answer = (payload or {}).get("answer", "")

    missing = [field for field in ("exam_id", "question_id", "answer_time_seconds", "submission_time_seconds") if (payload or {}).get(field) is None]
    if missing:
        raise BadRequestException(f"Missing required fields: {', '.join(missing)}")

    try:
        answer_time_seconds = float(answer_time_seconds)
        submission_time_seconds = float(submission_time_seconds)
        edit_count = int(edit_count)
    except (TypeError, ValueError):
        raise BadRequestException("answer_time_seconds, submission_time_seconds, and edit_count must be numeric")

    fast = is_fast_answer(answer_time_seconds)
    user_id = (user_context or {}).get("user_id")

    doc = {
        "exam_id": exam_id,
        "student_id": user_id,
        "question_id": question_id,
        "answer_time_seconds": answer_time_seconds,
        "submission_time_seconds": submission_time_seconds,
        "edit_count": edit_count,
        "answer": answer or "",
        "is_fast_answer": fast,
        "server_timestamp": now(),
    }

    try:
        behavioral_events_col.insert_one(doc)
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    # §24 bonus: push to WebSocket subscribers of this exam's room.
    from middleware.socketio_app import emit_monitoring_event
    emit_monitoring_event(exam_id, "behavioral_event", {
        "user_id": user_id, "exam_id": exam_id,
        "question_id": question_id,
        "answer_time_seconds": answer_time_seconds,
        "is_fast_answer": fast, "timestamp": now().isoformat(),
    })

    if fast:
        _send_log(
            LogLevel.SECURITY.value,
            user_id,
            "fast_answer_detected",
            {
                "exam_id": exam_id,
                "question_id": question_id,
                "answer_time_seconds": answer_time_seconds,
            },
        )

    return {
        "recorded": True,
        "is_fast_answer": fast,
        "answer_time_seconds": answer_time_seconds,
    }


def _fetch_exam_duration_seconds(exam_id):
    try:
        exam = exams_col.find_one({"_id": ObjectId(exam_id)})
    except Exception:
        exam = exams_col.find_one({"_id": exam_id})

    if not exam:
        raise BadRequestException("Exam not found")

    duration_minutes = int(exam.get("duration_minutes", 60))
    return duration_minutes * 60


def analyze_student_behavior(user_context, requested_user_id, exam_id):
    current_user = user_context or {}
    if requested_user_id and current_user.get("role") == "student" and requested_user_id != current_user.get("user_id"):
        raise ForbiddenException("Students cannot access other users' behavioral data")

    student_id = requested_user_id or current_user.get("user_id")
    if not exam_id:
        raise BadRequestException("exam_id is required")
    if not student_id:
        raise BadRequestException("student_id could not be determined")

    try:
        db_events = list(
            behavioral_events_col.find(
                {
                    "exam_id": exam_id,
                    "student_id": student_id,
                    "event_type": {"$ne": "analysis_result"},
                }
            ).sort("server_timestamp", 1)
        )
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    exam_duration_seconds = _fetch_exam_duration_seconds(exam_id)
    events = [
        {
            "question_id": str(e.get("question_id")),
            "answer_time_seconds": e.get("answer_time_seconds", 0),
            "submission_time_seconds": e.get("submission_time_seconds", 0),
            "edit_count": e.get("edit_count", 0),
        }
        for e in db_events
    ]

    # Pull clipboard paste timestamps for the §24 bonus clipboard-burst rule.
    paste_seconds = []
    try:
        clip_cursor = clipboard_events_col.find(
            {"exam_id": exam_id, "user_id": student_id, "event_type": "paste"}
        ).sort("server_timestamp", 1)
        clip_docs = list(clip_cursor)
        if clip_docs:
            base = clip_docs[0].get("server_timestamp")
            for doc in clip_docs:
                ts = doc.get("server_timestamp")
                if base and ts:
                    paste_seconds.append((ts - base).total_seconds())
    except PyMongoError:
        paste_seconds = []

    result = analyze_behavior(events, exam_duration_seconds, paste_seconds)

    summary_doc = {
        "exam_id": exam_id,
        "student_id": student_id,
        "event_type": "analysis_result",
        "analysis": result,
        "analyzed_at": now(),
    }

    try:
        behavioral_events_col.insert_one(summary_doc)
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    if result.get("suspicious_rule_count", 0) >= 2:
        _send_log(
            LogLevel.SECURITY.value,
            student_id,
            "suspicious_behavior_detected",
            {
                "exam_id": exam_id,
                "student_id": student_id,
                "suspicious_rule_count": result.get("suspicious_rule_count", 0),
                "flags": result.get("flags", {}),
            },
        )

    suspicious_rule_count = result.get("suspicious_rule_count", 0)
    if suspicious_rule_count >= 3:
        risk_level = "HIGH"
    elif suspicious_rule_count >= 1:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "exam_id": exam_id,
        "student_id": student_id,
        "analysis": result,
        "risk_level": risk_level,
    }


def get_summary(user_context, exam_id, requested_user_id=None):
    current_user = user_context or {}
    if requested_user_id and current_user.get("role") == "student":
        raise ForbiddenException("Students cannot access other users' behavioral summary")

    student_id = requested_user_id or current_user.get("user_id")
    if not exam_id:
        raise BadRequestException("exam_id is required")
    if not student_id:
        raise BadRequestException("student_id could not be determined")

    try:
        summary = behavioral_events_col.find_one(
            {
                "exam_id": exam_id,
                "student_id": student_id,
                "event_type": "analysis_result",
            },
            sort=[("analyzed_at", -1)],
        )
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    if not summary:
        return {"message": "No analysis run yet"}

    return summary.get("analysis", {})


def get_risk_data(user_id, exam_id):
    if not user_id:
        raise BadRequestException("user_id is required")
    if not exam_id:
        raise BadRequestException("exam_id is required")

    try:
        summary = behavioral_events_col.find_one(
            {"exam_id": exam_id, "student_id": user_id, "event_type": "analysis_result"},
            sort=[("analyzed_at", -1)],
        )
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    if not summary:
        return []

    analysis = summary.get("analysis", {})
    timestamp = now().isoformat()
    return [
        {
            "user_id": user_id,
            "exam_id": exam_id,
            "timestamp": timestamp,
            "metric": RiskMetric.FAST_ANSWER_COUNT.value,
            "value": analysis.get("fast_answer_count", 0),
        },
        {
            "user_id": user_id,
            "exam_id": exam_id,
            "timestamp": timestamp,
            "metric": RiskMetric.BULK_SUBMIT_FLAG.value,
            "value": analysis.get("bulk_submit_flag", 0),
        },
        {
            "user_id": user_id,
            "exam_id": exam_id,
            "timestamp": timestamp,
            "metric": RiskMetric.ANSWER_EDIT_COUNT.value,
            "value": analysis.get("answer_edit_count", 0),
        },
        {
            "user_id": user_id,
            "exam_id": exam_id,
            "timestamp": timestamp,
            "metric": RiskMetric.SUSPICIOUS_RULE_COUNT.value,
            "value": analysis.get("suspicious_rule_count", 0),
        },
    ]


def get_health():
    return {"module_name": ModuleName.BEHAVIORAL.value, "dependencies": ["mongodb"], "version": "1.0.0", "healthy": True}
