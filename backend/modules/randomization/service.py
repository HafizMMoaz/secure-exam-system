import hashlib
import random
import requests
from bson import ObjectId
from pymongo.errors import PyMongoError

from config.config import exams_col, questions_col, randomized_orders_col, BASE_URL, now, iso_utc_z
from enums.module_name import ModuleName
from enums.log_level import LogLevel
from enums.exam_state import ExamState
from exceptions import (
    BadRequestException,
    DatabaseException,
    ExamNotFoundException,
    ExamStateException,
    NotFoundException,
)


def _send_log(level, user_id, action, details):
    payload = {
        "module": ModuleName.RANDOMIZATION.value,
        "level": level,
        "user_id": user_id or "",
        "exam_id": details.get("exam_id") if details else "",
        "action": action,
        "details": details or {},
        "timestamp": iso_utc_z(),
    }
    try:
        requests.post(f"{BASE_URL}/api/logs/write", json=payload, timeout=2)
    except Exception:
        pass


def generate_randomized_order(user_context, payload):
    exam_id = (payload or {}).get("exam_id")
    if not exam_id:
        raise BadRequestException("exam_id is required")

    try:
        exam = exams_col.find_one({"_id": ObjectId(exam_id)})
    except Exception:
        raise ExamNotFoundException()

    if not exam:
        raise ExamNotFoundException()

    if exam.get("state") not in (ExamState.ACTIVATION_VALID.value, ExamState.IN_PROGRESS.value):
        raise ExamStateException(current_state=exam.get("state"), required_state=f"{ExamState.ACTIVATION_VALID.value} or {ExamState.IN_PROGRESS.value}")

    user_id = (user_context or {}).get("user_id")

    # Check idempotency
    try:
        existing = randomized_orders_col.find_one({"exam_id": exam_id, "student_id": user_id})
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    if existing:
        return {
            "exam_id": existing.get("exam_id"),
            "question_order": existing.get("question_order", []),
            "total_questions": len(existing.get("question_order", [])),
        }

    # Fetch questions
    try:
        cursor = list(questions_col.find({"exam_id": exam_id}).sort("order_index", 1))
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    question_ids = [str(q.get("_id")) for q in cursor]

    # Seed generation
    seed_str = f"{exam_id}_{user_id}"
    seed = int(hashlib.md5(seed_str.encode()).hexdigest(), 16) % (2 ** 32)
    rng = random.Random(seed)

    # Shuffle question order deterministically
    rng.shuffle(question_ids)

    # For each question create option shuffles using same RNG
    option_shuffles = []
    for q in cursor:
        qid = str(q.get("_id"))
        opts = q.get("options", [])[:]
        rng.shuffle(opts)
        option_shuffles.append({"question_id": qid, "shuffled_options": opts})

    doc = {
        "exam_id": exam_id,
        "student_id": user_id,
        "question_order": question_ids,
        "option_shuffles": option_shuffles,
        "seed": seed,
        "generated_at": now(),
    }

    try:
        randomized_orders_col.insert_one(doc)
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    _send_log(LogLevel.INFO.value, user_id, "randomization_generated", {"exam_id": exam_id, "student_id": user_id})

    return {"exam_id": exam_id, "question_order": question_ids, "total_questions": len(question_ids)}


def get_randomized_order(user_context, exam_id):
    if not exam_id:
        raise BadRequestException("exam_id is required")

    user_id = (user_context or {}).get("user_id")

    try:
        rec = randomized_orders_col.find_one({"exam_id": exam_id, "student_id": user_id})
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    if not rec:
        raise NotFoundException("Randomized order not generated yet. Call POST /api/randomization/generate first")

    return {"exam_id": rec.get("exam_id"), "question_order": rec.get("question_order", []), "total_questions": len(rec.get("question_order", []))}


def get_health():
    return {"module_name": ModuleName.RANDOMIZATION.value, "dependencies": ["mongodb"], "version": "1.0.0", "healthy": True}
