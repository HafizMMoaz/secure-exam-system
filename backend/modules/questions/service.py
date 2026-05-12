# §27.6 (refined): Module 6 owns the exam document body (title, duration, totals,
# enrollment list, teacher approval), all question CRUD, and student response writes
# (`answer_text`, `time_taken_seconds`, edit counts). State-machine writes to
# `exams_col.state` are NOT owned here — those belong to Modules 4, 8, and 17.
# Full rationale: ARCHITECTURE.md.
import hashlib
import json
import requests
from datetime import datetime
from bson import ObjectId
from pymongo.errors import PyMongoError
from pytz import utc

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
    ConflictException,
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
        "timestamp": now().astimezone(utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    try:
        requests.post(f"{BASE_URL}/api/logs/write", json=payload, timeout=2)
    except Exception:
        pass


def _serialize_dt(value):
    if value is None:
        return None
    normalized = _normalize_dt(value)
    return normalized.astimezone(utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_dt(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return utc.localize(value)
    return value


def _parse_iso_datetime(value):
    if not value:
        raise BadRequestException("start_time is required" if value is None else "end_time is required")
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        raise BadRequestException("Invalid datetime format")
    return _normalize_dt(parsed)


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
    max_students = (payload or {}).get("max_students", 30)
    start_time_raw = (payload or {}).get("start_time")
    end_time_raw = (payload or {}).get("end_time")

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

    try:
        max_students = int(max_students)
    except (TypeError, ValueError):
        raise BadRequestException("max_students must be an integer")

    if max_students < 1 or max_students > 200:
        raise BadRequestException("max_students must be between 1 and 200")

    if not start_time_raw:
        raise BadRequestException("start_time is required")
    if not end_time_raw:
        raise BadRequestException("end_time is required")

    start_time = _parse_iso_datetime(start_time_raw)
    end_time = _parse_iso_datetime(end_time_raw)

    if end_time <= start_time:
        raise BadRequestException("end_time must be after start_time")

    if (end_time - start_time).total_seconds() < duration_minutes * 60:
        raise BadRequestException("end_time must allow at least duration_minutes of exam time")

    exam_document = {
        "title": str(title).strip(),
        "description": str(description).strip(),
        "duration_minutes": duration_minutes,
        "max_students": max_students,
        "start_time": start_time,
        "end_time": end_time,
        "created_by": (user_context or {}).get("user_id"),
        "created_at": now(),
        "state": ExamState.NOT_STARTED.value,
        "students_approved": [],
        "enrolled_students": [],
        "students_count": 0,
        "total_questions": 0,
        "total_marks": 0,
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
                    "max_students": exam.get("max_students", 30),
                    "students_count": exam.get("students_count", 0),
                    "start_time": _serialize_dt(exam.get("start_time")),
                    "end_time": _serialize_dt(exam.get("end_time")),
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
        "max_students": exam.get("max_students", 30),
        "students_count": exam.get("students_count", 0),
        "total_questions": exam.get("total_questions", 0),
        "total_marks": exam.get("total_marks", 0),
        "start_time": _serialize_dt(exam.get("start_time")),
        "end_time": _serialize_dt(exam.get("end_time")),
        "state": exam.get("state"),
        "created_at": _serialize_dt(exam.get("created_at")),
        "created_by": exam.get("created_by"),
    }


def get_exam_public(exam_id):
    exam = _get_exam(exam_id)
    return {
        "exam_id": str(exam.get("_id")),
        "title": exam.get("title", ""),
        "description": exam.get("description", ""),
        "duration_minutes": exam.get("duration_minutes", 0),
        "state": exam.get("state"),
        "start_time": _serialize_dt(exam.get("start_time")),
        "end_time": _serialize_dt(exam.get("end_time")),
        "max_students": exam.get("max_students", 30),
        "students_count": exam.get("students_count", 0),
        "total_questions": exam.get("total_questions", 0),
        "total_marks": exam.get("total_marks", 0),
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

    count = questions_col.count_documents({"exam_id": exam_id})
    if count == 0:
        raise BadRequestException("Cannot approve exam with no questions. Add at least one question first.")

    # §27.6 (refined): Module 6 owns `state: TEACHER_APPROVED` — see ARCHITECTURE.md.
    try:
        exams_col.update_one(
            {"_id": exam.get("_id")},
            {"$set": {"state": ExamState.TEACHER_APPROVED.value}},
        )
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    _send_log(LogLevel.INFO.value, (user_context or {}).get("user_id"), "exam_approved", {"exam_id": str(exam.get("_id"))})

    return {"exam_id": str(exam.get("_id")), "state": ExamState.TEACHER_APPROVED.value}


def enroll_student(user_context, exam_id):
    if not exam_id:
        raise BadRequestException("exam_id is required")

    student_id = (user_context or {}).get("user_id")
    if not student_id:
        raise BadRequestException("student is required")

    exam = _get_exam(str(exam_id).strip())

    # Allow enrollment in TEACHER_APPROVED and IN_PROGRESS states
    if exam.get("state") not in {ExamState.TEACHER_APPROVED.value, ExamState.IN_PROGRESS.value}:
        raise ExamStateException(current_state=exam.get("state"), required_state=ExamState.TEACHER_APPROVED.value)

    current_time = now()
    start_time = _normalize_dt(exam.get("start_time"))
    end_time = _normalize_dt(exam.get("end_time"))

    if start_time and current_time < start_time:
        raise BadRequestException("Exam has not started yet")
    if end_time and current_time > end_time:
        raise BadRequestException("Exam has ended")

    # Check if already enrolled in students list
    students = exam.get("students", []) or []
    existing = next((s for s in students if s.get("student_id") == student_id), None)
    
    if existing:
        return {
            "already_enrolled": True,
            "exam_id": str(exam.get("_id")),
            "approved": existing.get("approved", False),
        }

    # For backward compatibility, also check enrolled_students
    enrolled_students = exam.get("enrolled_students", []) or []
    if student_id in enrolled_students:
        return {
            "already_enrolled": True,
            "exam_id": str(exam.get("_id")),
        }

    students_count = int(exam.get("students_count", 0) or 0)
    max_students = int(exam.get("max_students", 30) or 30)
    if students_count >= max_students:
        raise ConflictException("Exam is full")

    try:
        exams_col.update_one(
            {"_id": exam.get("_id")},
            {
                "$push": {
                    "students": {
                        "student_id": student_id,
                        "joined_at": now(),
                        "approved": False,
                        "approved_at": None,
                        "approved_by": None,
                    }
                },
                "$addToSet": {"enrolled_students": student_id},
                "$inc": {"students_count": 1},
            },
        )
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    return {
        "already_enrolled": False,
        "exam_id": str(exam.get("_id")),
        "start_time": _serialize_dt(start_time),
        "end_time": _serialize_dt(end_time),
        "duration_minutes": exam.get("duration_minutes", 0),
    }


def create_question(user_context, payload):
    exam_id = (payload or {}).get("exam_id")
    text = (payload or {}).get("text")
    options = (payload or {}).get("options")
    correct_answer = (payload or {}).get("correct_answer")
    marks = (payload or {}).get("marks")
    question_type = (payload or {}).get("question_type")
    word_limit = (payload or {}).get("word_limit", 0)

    missing = [k for k in ("exam_id", "text", "question_type", "marks") if (payload or {}).get(k) in (None, "")]
    if missing:
        raise BadRequestException(f"Missing required fields: {', '.join(missing)}")

    question_type = str(question_type).strip().lower()
    if question_type not in {"mcq", "text"}:
        raise BadRequestException("question_type must be 'mcq' or 'text'")

    try:
        marks = int(marks)
    except (TypeError, ValueError):
        raise BadRequestException("marks must be an integer")

    if marks < 1 or marks > 10:
        raise BadRequestException("marks must be between 1 and 10")

    try:
        word_limit = int(word_limit)
    except (TypeError, ValueError):
        raise BadRequestException("word_limit must be an integer")

    if word_limit < 0:
        raise BadRequestException("word_limit must be >= 0")

    if question_type == "mcq":
        if not isinstance(options, list) or len(options) != 4:
            raise BadRequestException("options must be a list of exactly 4 items for mcq")
        if not correct_answer:
            raise BadRequestException("correct_answer is required for mcq")
        if correct_answer not in options:
            raise BadRequestException("correct_answer must be one of the options")
    else:
        options = []
        correct_answer = ""

    if not text or not str(text).strip():
        raise BadRequestException("text is required")

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
            "question_type": question_type,
            "marks": marks,
            "word_limit": word_limit,
            "created_by": (user_context or {}).get("user_id"),
            "created_at": now(),
            "order_index": order_index,
        }
        result = questions_col.insert_one(doc)
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    update_exam_stats(exam_id)

    _send_log(LogLevel.INFO.value, (user_context or {}).get("user_id"), "question_created", {"exam_id": exam_id})
    return {"question_id": str(result.inserted_id)}


def update_exam_stats(exam_id):
    try:
        count = questions_col.count_documents({"exam_id": exam_id})
        marks_pipeline = [
            {"$match": {"exam_id": exam_id}},
            {"$group": {"_id": None, "total": {"$sum": "$marks"}}},
        ]
        result = list(questions_col.aggregate(marks_pipeline))
        total_marks = result[0]["total"] if result else 0
        exams_col.update_one(
            {"_id": ObjectId(exam_id)},
            {"$set": {"total_questions": count, "total_marks": total_marks}},
        )
    except Exception as exc:
        raise DatabaseException(str(exc))


def get_all_questions_for_student(user_context, exam_id):
    if not exam_id:
        raise BadRequestException("exam_id is required")

    try:
        exam = exams_col.find_one({"_id": ObjectId(exam_id)})
    except Exception:
        raise ExamNotFoundException()

    if not exam:
        raise ExamNotFoundException()

    if exam.get("state") != ExamState.IN_PROGRESS.value:
        raise ExamStateException(current_state=exam.get("state"), required_state=ExamState.IN_PROGRESS.value)

    try:
        cursor = questions_col.find({"exam_id": exam_id}).sort("order_index", 1)
        items = []
        for q in cursor:
            items.append(
                {
                    "question_id": str(q.get("_id")),
                    "text": q.get("text"),
                    "options": q.get("options", []),
                    "marks": q.get("marks", 0),
                    "order_index": q.get("order_index"),
                    "question_type": q.get("question_type", "mcq"),
                    "word_limit": q.get("word_limit", 0),
                }
            )
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    return {
        "questions": items,
        "total_questions": exam.get("total_questions", len(items)),
        "total_marks": exam.get("total_marks", 0),
    }


def save_answer(user_context, payload):
    exam_id = (payload or {}).get("exam_id")
    question_id = (payload or {}).get("question_id")
    answer = (payload or {}).get("answer")
    time_taken_seconds = (payload or {}).get("time_taken_seconds")
    student_id = (user_context or {}).get("user_id")

    missing = [
        field for field, value in (
            ("exam_id", exam_id),
            ("question_id", question_id),
            ("answer", answer),
            ("time_taken_seconds", time_taken_seconds),
        ) if value in (None, "")
    ]
    if missing:
        raise BadRequestException(f"Missing required fields: {', '.join(missing)}")

    exam = _get_exam(exam_id)
    if exam.get("state") != ExamState.IN_PROGRESS.value:
        raise ExamStateException(current_state=exam.get("state"), required_state=ExamState.IN_PROGRESS.value)

    question = questions_col.find_one({"_id": ObjectId(question_id), "exam_id": exam_id})
    if not question:
        raise BadRequestException("question_id is invalid for this exam")

    if question.get("question_type") == "text":
        word_limit = int(question.get("word_limit", 0) or 0)
        if word_limit > 0:
            words = str(answer).strip().split()
            if len(words) > word_limit:
                raise BadRequestException("Answer exceeds word_limit")

    try:
        time_taken_seconds = float(time_taken_seconds)
    except (TypeError, ValueError):
        raise BadRequestException("time_taken_seconds must be a number")

    if time_taken_seconds < 0:
        raise BadRequestException("time_taken_seconds must be >= 0")

    try:
        responses_col.update_one(
            {
                "exam_id": exam_id,
                "student_id": student_id,
                "question_id": question_id,
            },
            {
                "$set": {
                    "answer_text": answer,
                    "time_taken_seconds": time_taken_seconds,
                    "updated_at": now(),
                },
                "$setOnInsert": {
                    "exam_id": exam_id,
                    "student_id": student_id,
                    "question_id": question_id,
                    "created_at": now(),
                },
                "$inc": {"edit_count": 1},
            },
            upsert=True,
        )
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    return {"saved": True, "question_id": question_id}


def get_student_answers(user_context, exam_id):
    if not exam_id:
        raise BadRequestException("exam_id is required")

    student_id = (user_context or {}).get("user_id")

    try:
        cursor = responses_col.find({"exam_id": exam_id, "student_id": student_id})
        answers = {}
        for response in cursor:
            answers[str(response.get("question_id"))] = response.get("answer_text", response.get("answer", ""))
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    return {"answers": answers}


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
                    "question_type": q.get("question_type", "mcq"),
                    "word_limit": q.get("word_limit", 0),
                }
            )
        return {"questions": items, "count": len(items)}
    except PyMongoError as exc:
        raise DatabaseException(str(exc))


def update_exam(user_context, exam_id, payload):
    if not exam_id:
        raise BadRequestException("exam_id is required")

    exam = _get_exam(str(exam_id).strip())

    if not _is_teacher_exam_owner(user_context, exam):
        raise ForbiddenException("You are not allowed to edit this exam")

    current_state = exam.get("state")
    if current_state not in {ExamState.NOT_STARTED.value}:
        raise ExamStateException("Cannot edit exam once it has started")

    updates = {}

    title = (payload or {}).get("title")
    if title is not None:
        if not str(title).strip():
            raise BadRequestException("title cannot be empty")
        updates["title"] = str(title).strip()

    description = (payload or {}).get("description")
    if description is not None:
        updates["description"] = str(description).strip() if description else ""

    duration_minutes = (payload or {}).get("duration_minutes")
    if duration_minutes is not None:
        try:
            duration_minutes = int(duration_minutes)
        except (TypeError, ValueError):
            raise BadRequestException("duration_minutes must be an integer")
        if duration_minutes < 10 or duration_minutes > 180:
            raise BadRequestException("duration_minutes must be between 10 and 180")
        updates["duration_minutes"] = duration_minutes

    max_students = (payload or {}).get("max_students")
    if max_students is not None:
        try:
            max_students = int(max_students)
        except (TypeError, ValueError):
            raise BadRequestException("max_students must be an integer")
        if max_students < 1 or max_students > 200:
            raise BadRequestException("max_students must be between 1 and 200")
        current_count = int(exam.get("students_count", 0) or 0)
        if max_students < current_count:
            raise BadRequestException("max_students cannot be less than current enrolled students")
        updates["max_students"] = max_students

    start_time = None
    end_time = None

    start_time_raw = (payload or {}).get("start_time")
    if start_time_raw is not None:
        start_time = _parse_iso_datetime(start_time_raw)
        updates["start_time"] = start_time

    end_time_raw = (payload or {}).get("end_time")
    if end_time_raw is not None:
        end_time = _parse_iso_datetime(end_time_raw)
        updates["end_time"] = end_time

    if start_time is None:
        start_time = exam.get("start_time")
    if end_time is None:
        end_time = exam.get("end_time")

    if start_time and end_time:
        if end_time <= start_time:
            raise BadRequestException("end_time must be after start_time")
        duration = updates.get("duration_minutes", exam.get("duration_minutes", 0))
        if (end_time - start_time).total_seconds() < duration * 60:
            raise BadRequestException("end_time must allow at least duration_minutes of exam time")

    if not updates:
        raise BadRequestException("No fields to update")

    try:
        exams_col.update_one(
            {"_id": exam.get("_id")},
            {"$set": updates},
        )
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    _send_log(LogLevel.INFO.value, (user_context or {}).get("user_id"), "exam_updated", {"exam_id": exam_id})

    return {"exam_id": exam_id, "updated": True}


def delete_exam(user_context, exam_id):
    if not exam_id:
        raise BadRequestException("exam_id is required")

    exam = _get_exam(str(exam_id).strip())

    if not _is_teacher_exam_owner(user_context, exam):
        raise ForbiddenException("You are not allowed to delete this exam")

    current_state = exam.get("state")
    if current_state not in {ExamState.NOT_STARTED.value}:
        raise ExamStateException("Cannot delete exam once it has started")

    students_count = int(exam.get("students_count", 0) or 0)
    if students_count > 0:
        raise ConflictException("Cannot delete exam with enrolled students")

    try:
        exams_col.delete_one({"_id": exam.get("_id")})
        questions_col.delete_many({"exam_id": exam_id})
        responses_col.delete_many({"exam_id": exam_id})
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    _send_log(LogLevel.INFO.value, (user_context or {}).get("user_id"), "exam_deleted", {"exam_id": exam_id})

    return {"exam_id": exam_id, "deleted": True}


def update_question(user_context, question_id, payload):
    if not question_id:
        raise BadRequestException("question_id is required")

    try:
        question = questions_col.find_one({"_id": ObjectId(question_id)})
    except Exception:
        raise BadRequestException("Invalid question_id")

    if not question:
        raise BadRequestException("Question not found")

    exam_id = question.get("exam_id")
    exam = _get_exam(exam_id)

    if not _is_teacher_exam_owner(user_context, exam):
        raise ForbiddenException("You are not allowed to edit this question")

    updates = {}

    text = (payload or {}).get("text")
    if text is not None:
        if not str(text).strip():
            raise BadRequestException("text cannot be empty")
        updates["text"] = str(text).strip()

    question_type = (payload or {}).get("question_type")
    if question_type is not None:
        question_type = str(question_type).strip().lower()
        if question_type not in {"mcq", "text"}:
            raise BadRequestException("question_type must be 'mcq' or 'text'")
        updates["question_type"] = question_type

    marks = (payload or {}).get("marks")
    if marks is not None:
        try:
            marks = int(marks)
        except (TypeError, ValueError):
            raise BadRequestException("marks must be an integer")
        if marks < 1 or marks > 10:
            raise BadRequestException("marks must be between 1 and 10")
        updates["marks"] = marks

    word_limit = (payload or {}).get("word_limit")
    if word_limit is not None:
        try:
            word_limit = int(word_limit)
        except (TypeError, ValueError):
            raise BadRequestException("word_limit must be an integer")
        if word_limit < 0:
            raise BadRequestException("word_limit must be >= 0")
        updates["word_limit"] = word_limit

    options = (payload or {}).get("options")
    correct_answer = (payload or {}).get("correct_answer")
    qt = updates.get("question_type", question.get("question_type", "mcq"))

    if qt == "mcq":
        if options is not None:
            if not isinstance(options, list) or len(options) != 4:
                raise BadRequestException("options must be a list of exactly 4 items for mcq")
            updates["options"] = options
        if correct_answer is not None:
            if not correct_answer:
                raise BadRequestException("correct_answer is required for mcq")
            opts = options if options is not None else question.get("options", [])
            if correct_answer not in opts:
                raise BadRequestException("correct_answer must be one of the options")
            updates["correct_answer"] = correct_answer
    else:
        updates["options"] = []
        updates["correct_answer"] = ""

    if not updates:
        raise BadRequestException("No fields to update")

    try:
        questions_col.update_one(
            {"_id": question.get("_id")},
            {"$set": updates},
        )
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    update_exam_stats(exam_id)

    _send_log(LogLevel.INFO.value, (user_context or {}).get("user_id"), "question_updated", {"exam_id": exam_id, "question_id": question_id})

    return {"question_id": question_id, "updated": True}


def delete_question(user_context, question_id):
    if not question_id:
        raise BadRequestException("question_id is required")

    try:
        question = questions_col.find_one({"_id": ObjectId(question_id)})
    except Exception:
        raise BadRequestException("Invalid question_id")

    if not question:
        raise BadRequestException("Question not found")

    exam_id = question.get("exam_id")
    exam = _get_exam(exam_id)

    if not _is_teacher_exam_owner(user_context, exam):
        raise ForbiddenException("You are not allowed to delete this question")

    try:
        questions_col.delete_one({"_id": question.get("_id")})
        responses_col.delete_many({"question_id": question_id})

        deleted_order = question.get("order_index", 0)
        questions_col.update_many(
            {"exam_id": exam_id, "order_index": {"$gt": deleted_order}},
            {"$inc": {"order_index": -1}},
        )
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    update_exam_stats(exam_id)

    _send_log(LogLevel.INFO.value, (user_context or {}).get("user_id"), "question_deleted", {"exam_id": exam_id, "question_id": question_id})

    return {"question_id": question_id, "deleted": True}


def approve_student(user_context, payload):
    exam_id = (payload or {}).get("exam_id")
    student_id = (payload or {}).get("student_id")
    
    if not exam_id:
        raise BadRequestException("exam_id is required")
    if not student_id:
        raise BadRequestException("student_id is required")

    exam = _get_exam(str(exam_id).strip())
    
    if not _is_teacher_exam_owner(user_context, exam):
        raise ForbiddenException("You are not allowed to approve students for this exam")

    try:
        exams_col.update_one(
            {"_id": exam.get("_id"), "students.student_id": student_id},
            {
                "$set": {
                    "students.$.approved": True,
                    "students.$.approved_at": now(),
                    "students.$.approved_by": (user_context or {}).get("user_id"),
                }
            },
        )
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    _send_log(LogLevel.INFO.value, (user_context or {}).get("user_id"), "student_approved", {"exam_id": exam_id, "student_id": student_id})

    return {"exam_id": exam_id, "student_id": student_id, "approved": True}


def get_exam_students(user_context, exam_id):
    if not exam_id:
        raise BadRequestException("exam_id is required")

    exam = _get_exam(str(exam_id).strip())
    
    if not _is_teacher_exam_owner(user_context, exam):
        raise ForbiddenException("You are not allowed to view students for this exam")

    students = exam.get("students", []) or []
    result = []
    
    for student in students:
        result.append({
            "student_id": student.get("student_id"),
            "joined_at": _serialize_dt(student.get("joined_at")),
            "approved": student.get("approved", False),
            "approved_at": _serialize_dt(student.get("approved_at")),
            "approved_by": student.get("approved_by"),
        })
    
    return {"exam_id": exam_id, "students": result, "count": len(result)}


def get_health():
    return {"module_name": ModuleName.QUESTIONS.value, "dependencies": ["mongodb"], "version": "1.0.0", "healthy": True}
