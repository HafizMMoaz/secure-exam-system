import hashlib
import json
import requests
from bson import ObjectId
from pymongo.errors import PyMongoError

from config.config import questions_col, exams_col, responses_col, BASE_URL, now
from enums.module_name import ModuleName
from enums.log_level import LogLevel
from enums.exam_state import ExamState
from exceptions import (
    BadRequestException,
    DatabaseException,
    ExamStateException,
    ExamNotFoundException,
    ForbiddenException,
)


def _iso_dt(value):
    if value is None:
        return None
    return value.replace(microsecond=0).isoformat() + "Z"


def _send_log(level, user_id, action, details):
    payload = {
        "module": ModuleName.QUESTIONS.value,
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


def _serialize_dt(value):
    if value is None:
        return None
    return value.replace(microsecond=0).isoformat() + "Z"


def _get_exam(exam_id):
    try:
        exam = exams_col.find_one({"_id": ObjectId(exam_id)})
    except Exception:
        raise ExamNotFoundException()

    if not exam:
        raise ExamNotFoundException()
    return exam


def _is_teacher_exam_owner(user_context, exam):
    return str(exam.get("created_by")) == str((user_context or {}).get("user_id"))


def create_exam(user_context, payload):
    title = (payload or {}).get("title")
    description = (payload or {}).get("description", "") or ""
    duration_minutes = (payload or {}).get("duration_minutes")

    if not title or not str(title).strip():
        raise BadRequestException("title is required")
    if duration_minutes is None:
        raise BadRequestException("duration_minutes is required")

    try:
        duration_minutes = int(duration_minutes)
    except (TypeError, ValueError):
        raise BadRequestException("duration_minutes must be an integer")

    if duration_minutes < 10 or duration_minutes > 180:
        raise BadRequestException("duration_minutes must be between 10 and 180")

    exam_document = {
        "title": str(title).strip(),
        "description": str(description).strip(),
        "duration_minutes": duration_minutes,
        "created_by": (user_context or {}).get("user_id"),
        "created_at": now(),
        "state": ExamState.NOT_STARTED.value,
        "students_approved": [],
    }

    try:
        result = exams_col.insert_one(exam_document)
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    exam_id = str(result.inserted_id)
    _send_log(LogLevel.INFO.value, (user_context or {}).get("user_id"), "exam_created", {"title": exam_document["title"], "exam_id": exam_id})

    return {
        "exam_id": exam_id,
        "title": exam_document["title"],
        "state": ExamState.NOT_STARTED.value,
        "duration_minutes": duration_minutes,
    }


def list_exams(user_context):
    try:
        cursor = exams_col.find({"created_by": (user_context or {}).get("user_id")}).sort("created_at", -1)
        exams = []
        for exam in cursor:
            exams.append(
                {
                    "exam_id": str(exam.get("_id")),
                    "title": exam.get("title", ""),
                    "description": exam.get("description", ""),
                    "duration_minutes": exam.get("duration_minutes", 0),
                    "state": exam.get("state"),
                    "created_at": _serialize_dt(exam.get("created_at")),
                }
            )
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    return {"exams": exams, "count": len(exams)}


def get_exam(exam_id):
    exam = _get_exam(exam_id)
    return {
        "exam_id": str(exam.get("_id")),
        "title": exam.get("title", ""),
        "description": exam.get("description", ""),
        "duration_minutes": exam.get("duration_minutes", 0),
        "state": exam.get("state"),
        "created_at": _serialize_dt(exam.get("created_at")),
        "created_by": exam.get("created_by"),
    }


def approve_exam(user_context, payload):
    exam_id = (payload or {}).get("exam_id")
    if not exam_id:
        raise BadRequestException("exam_id is required")

    exam = _get_exam(str(exam_id).strip())

    if not _is_teacher_exam_owner(user_context, exam):
        raise ForbiddenException("You are not allowed to approve this exam")

    current_state = exam.get("state")
    if current_state not in {ExamState.NOT_STARTED.value, ExamState.DEVICE_VERIFIED.value}:
        raise ExamStateException("Exam already approved or past approval stage")

    try:
        exams_col.update_one(
            {"_id": exam.get("_id")},
            {"$set": {"state": ExamState.TEACHER_APPROVED.value}},
        )
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    _send_log(LogLevel.INFO.value, (user_context or {}).get("user_id"), "exam_approved", {"exam_id": str(exam.get("_id"))})

    return {"exam_id": str(exam.get("_id")), "state": ExamState.TEACHER_APPROVED.value}


def create_question(user_context, payload):
    exam_id = (payload or {}).get("exam_id")
    text = (payload or {}).get("text")
    options = (payload or {}).get("options")
    correct_answer = (payload or {}).get("correct_answer")
    marks = (payload or {}).get("marks", 1)

    # Validate required
    missing = [k for k in ("exam_id", "text", "options", "correct_answer") if not (payload or {}).get(k)]
    if missing:
        raise BadRequestException(f"Missing required fields: {', '.join(missing)}")

    if not isinstance(options, list) or len(options) != 4:
        raise BadRequestException("options must be a list of exactly 4 items")

    if correct_answer not in options:
        raise BadRequestException("correct_answer must be one of the options")

    try:
        exam = exams_col.find_one({"_id": ObjectId(exam_id)})
    except Exception:
        raise ExamNotFoundException()

    if not exam:
        raise ExamNotFoundException()

    try:
        order_index = questions_col.count_documents({"exam_id": exam_id}) + 1
        doc = {
            "exam_id": exam_id,
            "text": text,
            "options": options,
            "correct_answer": correct_answer,
            "marks": int(marks) if marks is not None else 1,
            "created_by": (user_context or {}).get("user_id"),
            "created_at": now(),
            "order_index": order_index,
        }
        result = questions_col.insert_one(doc)
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    _send_log(LogLevel.INFO.value, (user_context or {}).get("user_id"), "question_created", {"exam_id": exam_id})
    return {"question_id": str(result.inserted_id)}


def next_question(user_context, exam_id):
    if not exam_id:
        raise BadRequestException("exam_id is required")

    try:
        exam = exams_col.find_one({"_id": ObjectId(exam_id)})
    except Exception:
        raise ExamNotFoundException()

    if not exam:
        raise ExamNotFoundException()

    if exam.get("state") != ExamState.IN_PROGRESS.value:
        raise Exception(  # will be handled by caller as ExamStateException
            {
                "current_state": exam.get("state"),
                "required_state": ExamState.IN_PROGRESS,
            }
        )

    user_id = (user_context or {}).get("user_id")

    try:
        answered_cursor = responses_col.find({"exam_id": exam_id, "student_id": user_id})
        answered_ids = {str(r.get("question_id")) for r in answered_cursor}

        query = {"exam_id": exam_id}
        cursor = questions_col.find(query).sort("order_index", 1)

        next_q = None
        for q in cursor:
            qid = str(q.get("_id"))
            if qid in answered_ids:
                continue
            next_q = q
            break
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    if not next_q:
        return {"question": None, "message": "All questions answered", "exam_complete": True}

    _send_log(LogLevel.INFO.value, user_id, "question_delivered", {"exam_id": exam_id, "question_id": str(next_q.get("_id"))})

    return {
        "question": {
            "question_id": str(next_q.get("_id")),
            "text": next_q.get("text"),
            "options": next_q.get("options"),
            "marks": next_q.get("marks"),
            "order_index": next_q.get("order_index"),
        },
        "exam_complete": False,
    }


def list_questions(exam_id):
    if not exam_id:
        raise BadRequestException("exam_id is required")

    try:
        cursor = questions_col.find({"exam_id": exam_id}).sort("order_index", 1)
        items = []
        for q in cursor:
            items.append(
                {
                    "question_id": str(q.get("_id")),
                    "exam_id": q.get("exam_id"),
                    "text": q.get("text"),
                    "options": q.get("options"),
                    "correct_answer": q.get("correct_answer"),
                    "marks": q.get("marks"),
                    "order_index": q.get("order_index"),
                }
            )
        return {"questions": items, "count": len(items)}
    except PyMongoError as exc:
        raise DatabaseException(str(exc))


def get_health():
    return {"module_name": ModuleName.QUESTIONS.value, "dependencies": ["mongodb"], "version": "1.0.0", "healthy": True}
