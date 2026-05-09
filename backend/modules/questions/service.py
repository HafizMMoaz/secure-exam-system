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
    ExamNotFoundException,
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
