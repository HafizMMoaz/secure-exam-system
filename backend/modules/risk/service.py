import requests
from bson import ObjectId
from pymongo.errors import PyMongoError

from config.config import responses_col, behavioral_events_col, exams_col, users_col, risk_scores_col, BASE_URL, now
from enums.module_name import ModuleName
from enums.log_level import LogLevel
from enums.risk_metric import RiskMetric
from enums.exam_state import ExamState
from exceptions import BadRequestException, DatabaseException, ExamNotFoundException, ForbiddenException, ExamStateException


RISK_DATA_ENDPOINTS = [
    ("tab_switch_count", "/api/tab/risk-data"),
    ("clipboard_paste_count", "/api/clipboard/risk-data"),
    ("idle_time_seconds", "/api/activity/risk-data"),
    ("multi_session_attempts", "/api/multisession/risk-data"),
    ("fast_answer_count", "/api/behavioral/risk-data"),
    ("similarity_score", "/api/similarity/risk-data"),
]


def _iso(dt):
    if dt is None:
        return None
    return dt.isoformat()


def _send_log(level, user_id, action, details):
    payload = {
        "module": ModuleName.RISK.value,
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


def _load_exam(exam_id):
    try:
        exam = exams_col.find_one({"_id": ObjectId(exam_id)})
    except Exception:
        exam = exams_col.find_one({"_id": exam_id})
    if not exam:
        raise ExamNotFoundException()
    return exam


def _get_student_ids(exam_id):
    student_ids = responses_col.distinct("student_id", {"exam_id": exam_id})
    if not student_ids:
        student_ids = behavioral_events_col.distinct("student_id", {"exam_id": exam_id})
    return [str(student_id) for student_id in student_ids if student_id is not None]


def _fetch_metrics_for_student(student_id, exam_id, auth_header):
    headers = {"Authorization": auth_header}
    metrics = {}

    for _, endpoint in RISK_DATA_ENDPOINTS:
        url = f"{BASE_URL}{endpoint}?user_id={student_id}&exam_id={exam_id}"
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code != 200:
                continue
            payload = response.json() or {}
            for item in payload.get("data", []):
                metrics[item.get("metric")] = item.get("value")
        except Exception:
            continue

    return metrics


def _compute_score(metrics):
    tab_switches = metrics.get(RiskMetric.TAB_SWITCH_COUNT.value, 0)
    idle_seconds = metrics.get(RiskMetric.IDLE_TIME_SECONDS.value, 0)
    similarity = metrics.get(RiskMetric.SIMILARITY_SCORE.value, 0.0)
    fast_answers = metrics.get(RiskMetric.FAST_ANSWER_COUNT.value, 0)

    idle_normalized = min(idle_seconds / 300, 1) * 10
    score = (0.3 * tab_switches) + (0.2 * idle_normalized) + (0.3 * similarity * 10) + (0.2 * fast_answers)
    score = round(min(max(score, 0), 10), 2)

    risk_level = "HIGH" if score >= 7 else "MEDIUM" if score >= 4 else "LOW"
    return score, risk_level


def compute_exam_risk(user_context, exam_id, auth_header):
    if not exam_id:
        raise BadRequestException("exam_id is required")

    if (user_context or {}).get("role") != "teacher":
        raise ForbiddenException("Only teachers can compute risk scores")

    exam = _load_exam(exam_id)
    current_state = exam.get("state")
    if current_state not in (ExamState.SUBMITTED.value, ExamState.ANALYZING.value):
        raise ExamStateException(
            current_state=current_state,
            required_state=f"{ExamState.SUBMITTED.value} or {ExamState.ANALYZING.value}",
        )

    # §27.4 SUBMITTED → ANALYZING transition; idempotent if already ANALYZING.
    # §27.6 (refined): Module 17 owns `state: ANALYZING/COMPLETED` — see ARCHITECTURE.md.
    if current_state == ExamState.SUBMITTED.value:
        try:
            exams_col.update_one(
                {"_id": exam.get("_id")},
                {"$set": {"state": ExamState.ANALYZING.value}},
            )
        except PyMongoError as exc:
            raise DatabaseException(str(exc))
        _send_log(
            LogLevel.INFO.value,
            (user_context or {}).get("user_id"),
            "exam_state_transition",
            {"exam_id": exam_id, "from": ExamState.SUBMITTED.value, "to": ExamState.ANALYZING.value},
        )

    student_ids = _get_student_ids(exam_id)
    results = []

    for student_id in student_ids:
        metrics = _fetch_metrics_for_student(student_id, exam_id, auth_header)
        score, risk_level = _compute_score(metrics)

        doc = {
            "exam_id": exam_id,
            "student_id": student_id,
            "score": score,
            "risk_level": risk_level,
            "metrics": metrics,
            "computed_at": now(),
            "computed_by": (user_context or {}).get("user_id"),
        }

        try:
            risk_scores_col.insert_one(doc)
        except PyMongoError as exc:
            raise DatabaseException(str(exc))

        if score >= 7:
            level = LogLevel.SECURITY.value
        elif score >= 4:
            level = LogLevel.WARNING.value
        else:
            level = LogLevel.INFO.value

        _send_log(level, (user_context or {}).get("user_id"), "risk_score_computed", {"student_id": student_id, "score": score, "risk_level": risk_level, "exam_id": exam_id})

        results.append({"student_id": student_id, "score": score, "risk_level": risk_level, "metrics": metrics})

    try:
        # §27.6 (refined): Module 17 owns `state: COMPLETED` — see ARCHITECTURE.md.
        exams_col.update_one({"_id": exam.get("_id")}, {"$set": {"state": ExamState.COMPLETED.value}})
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    return {
        "exam_id": exam_id,
        "students_scored": len(results),
        "results": results,
        "exam_state": ExamState.COMPLETED.value,
    }


def get_dashboard(exam_id):
    if not exam_id:
        raise BadRequestException("exam_id is required")

    try:
        cursor = list(risk_scores_col.find({"exam_id": exam_id}).sort("score", -1))
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    total_students = len(cursor)
    high_risk_count = 0
    medium_risk_count = 0
    low_risk_count = 0
    total_score = 0.0

    students = []
    for record in cursor:
        score = float(record.get("score", 0))
        risk_level = record.get("risk_level", "LOW")
        total_score += score
        if risk_level == "HIGH":
            high_risk_count += 1
        elif risk_level == "MEDIUM":
            medium_risk_count += 1
        else:
            low_risk_count += 1

        student_id = record.get("student_id")
        try:
            user_doc = users_col.find_one({"_id": ObjectId(student_id)}) or {}
        except Exception:
            user_doc = users_col.find_one({"_id": student_id}) or {}
        students.append(
            {
                "student_id": record.get("student_id"),
                "username": user_doc.get("username", ""),
                "score": score,
                "risk_level": risk_level,
                "metrics": record.get("metrics", {}),
                "computed_at": _iso(record.get("computed_at")),
            }
        )

    average_score = round(total_score / total_students, 2) if total_students else 0.0
    return {
        "exam_id": exam_id,
        "total_students": total_students,
        "high_risk_count": high_risk_count,
        "medium_risk_count": medium_risk_count,
        "low_risk_count": low_risk_count,
        "average_score": average_score,
        "students": students,
    }


def get_student_score(user_context, student_id, exam_id):
    if not exam_id:
        raise BadRequestException("exam_id is required")

    current_user = user_context or {}
    if current_user.get("role") == "student" and student_id != current_user.get("user_id"):
        raise ForbiddenException("Students can only access their own risk score")

    try:
        record = risk_scores_col.find_one({"student_id": student_id, "exam_id": exam_id}, sort=[("computed_at", -1)])
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    if not record:
        return {"message": "Risk score not yet computed for this student"}

    return {
        "student_id": record.get("student_id"),
        "exam_id": record.get("exam_id"),
        "score": record.get("score", 0),
        "risk_level": record.get("risk_level", "LOW"),
        "metrics": record.get("metrics", {}),
        "computed_at": _iso(record.get("computed_at")),
    }


def get_health():
    return {"module_name": ModuleName.RISK.value, "dependencies": ["mongodb"], "version": "1.0.0", "healthy": True}
