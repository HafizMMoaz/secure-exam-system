"""
Pytest fixtures for PRD §27.8 integration tests.
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
