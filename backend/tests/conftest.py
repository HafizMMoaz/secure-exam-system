"""
Pytest fixtures for PRD section 27.8 integration tests.
"""

import os
import time

import bcrypt
import jwt
import pytest
from bson import ObjectId
from pymongo import MongoClient


BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5500")
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://127.0.0.1:27017/exam_security")
JWT_SECRET = os.environ.get("JWT_SECRET", "ci_test_secret_change_me")


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def db():
    client = MongoClient(MONGO_URI)
    return client.get_default_database()


@pytest.fixture(autouse=True)
def clean_db(db):
    for col in ("users", "exams", "questions", "responses", "tab_events",
                "logs", "exam_sessions"):
        db[col].delete_many({})
    yield


def _reseed_demo(db):
    """
    Tests wipe the shared dev database between cases. Without this, running
    pytest leaves the dev login broken (teach_demo / stud_demo gone).
    Re-create the demo users + their exam at session teardown so the app
    stays usable straight after the suite.
    """
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)

    teacher_id = ObjectId()
    student_id = ObjectId()
    student2_id = ObjectId()

    def h(pw):
        return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

    db.users.insert_many([
        {"_id": teacher_id, "username": "teach_demo", "password_hash": h("demo_pass"),
         "role": "teacher", "is_active": True, "created_at": now},
        {"_id": student_id, "username": "stud_demo", "password_hash": h("demo_pass"),
         "role": "student", "is_active": True, "created_at": now},
        {"_id": student2_id, "username": "stud_alice", "password_hash": h("demo_pass"),
         "role": "student", "is_active": True, "created_at": now},
    ])

    exam_id = ObjectId()
    db.exams.insert_one({
        "_id": exam_id,
        "title": "Demo Exam — Math",
        "description": "Walkthrough exam for the final viva",
        "duration_minutes": 30,
        "created_by": str(teacher_id),
        "teacher_id": str(teacher_id),
        "state": "ACTIVATION_VALID",
        "total_questions": 3,
        "total_marks": 30,
        "students_count": 2,
        "max_students": 10,
        "starts_at": now,
        "ends_at": now + timedelta(hours=2),
        "created_at": now,
        "enrolled_students": [
            {"student_id": str(student_id), "approved": True, "joined_at": now,
             "approved_at": now, "approved_by": str(teacher_id)},
            {"student_id": str(student2_id), "approved": True, "joined_at": now,
             "approved_at": now, "approved_by": str(teacher_id)},
        ],
    })
    db.activation_codes.insert_one({
        "exam_id": str(exam_id),
        "code": "DEMO123",
        "used": False,
        "expires_at": now + timedelta(hours=2),
        "created_at": now,
    })


@pytest.fixture(scope="session", autouse=True)
def reseed_demo_on_teardown(db):
    yield
    try:
        _reseed_demo(db)
    except Exception as exc:
        print(f"[conftest] reseed_demo failed: {exc}")


def _mint(payload, expiry_seconds=600):
    body = {"exp": int(time.time()) + expiry_seconds, **payload}
    return jwt.encode(body, JWT_SECRET, algorithm="HS256")


@pytest.fixture
def teacher_token():
    teacher_id = str(ObjectId())
    token = _mint({
        "user_id": teacher_id,
        "username": "t_pytest",
        "role": "teacher",
        "session_id": "s_pytest",
        "device_fingerprint_hash": "fp_pytest",
    })
    return token, teacher_id


@pytest.fixture
def student_token():
    student_id = str(ObjectId())
    token = _mint({
        "user_id": student_id,
        "username": "s_pytest",
        "role": "student",
        "session_id": "s_pytest_stud",
        "device_fingerprint_hash": "fp_pytest_stud",
    })
    return token, student_id


@pytest.fixture
def expired_teacher_token():
    return _mint({
        "user_id": str(ObjectId()),
        "username": "t_pytest",
        "role": "teacher",
        "session_id": "s_pytest",
        "device_fingerprint_hash": "fp_pytest",
    }, expiry_seconds=-10)


@pytest.fixture
def seeded_exam(db, teacher_token, student_token):
    _, teacher_id = teacher_token
    _, student_id = student_token

    db.users.insert_many([
        {
            "_id": ObjectId(teacher_id),
            "username": "t_pytest",
            "password_hash": bcrypt.hashpw(b"x", bcrypt.gensalt()).decode(),
            "role": "teacher",
            "is_active": True,
        },
        {
            "_id": ObjectId(student_id),
            "username": "s_pytest",
            "password_hash": bcrypt.hashpw(b"x", bcrypt.gensalt()).decode(),
            "role": "student",
            "is_active": True,
        },
    ])

    exam_id = ObjectId()
    question_id = ObjectId()
    db.exams.insert_one({
        "_id": exam_id,
        "title": "Pytest Exam",
        "duration_minutes": 30,
        "teacher_id": teacher_id,
        "state": "NOT_STARTED",
        "total_questions": 1,
        "total_marks": 10,
        "students_count": 1,
        "max_students": 5,
        "enrolled_students": [{"student_id": student_id, "approved": True}],
    })
    db.questions.insert_one({
        "_id": question_id,
        "exam_id": str(exam_id),
        "question_text": "Q?",
        "question_type": "text",
        "marks": 10,
        "order_index": 0,
        "word_limit": 100,
    })

    return {"exam_id": str(exam_id), "question_id": str(question_id),
            "teacher_id": teacher_id, "student_id": student_id}
