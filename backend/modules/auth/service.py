from datetime import datetime, timedelta
from uuid import uuid4

import bcrypt
import jwt
from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import DuplicateKeyError, PyMongoError

from config.config import JWT_SECRET, JWT_EXPIRY_MINUTES, users_col, exams_col
from enums.user_role import UserRole
from enums.module_name import ModuleName
from exceptions import (
    BadRequestException,
    DatabaseException,
    ExamNotFoundException,
    UnauthorizedException,
    UserAlreadyExistsException,
    UserNotFoundException,
)


def _validate_required_fields(payload, required_fields):
    missing_fields = [field for field in required_fields if not payload.get(field)]
    if missing_fields:
        raise BadRequestException(
            f"Missing required fields: {', '.join(missing_fields)}"
        )


def _serialize_created_at(created_at):
    if isinstance(created_at, datetime):
        return created_at.replace(microsecond=0).isoformat() + "Z"
    return created_at


def _normalize_text(value):
    return str(value).strip()


def register_user(payload):
    _validate_required_fields(payload, ["username", "password", "role"])

    username = _normalize_text(payload["username"])
    password = payload["password"]
    role = _normalize_text(payload["role"])

    valid_roles = {user_role.value for user_role in UserRole}
    if role not in valid_roles:
        raise BadRequestException("role must be 'student' or 'teacher'")

    try:
        existing_user = users_col.find_one({"username": username})
        if existing_user:
            raise UserAlreadyExistsException()

        password_hash = bcrypt.hashpw(
            _normalize_text(password).encode("utf-8"),
            bcrypt.gensalt(),
        ).decode("utf-8")

        user_document = {
            "username": username,
            "password_hash": password_hash,
            "role": role,
            "created_at": datetime.utcnow(),
            "is_active": True,
        }

        result = users_col.insert_one(user_document)
        return {"user_id": str(result.inserted_id)}
    except UserAlreadyExistsException:
        raise
    except DuplicateKeyError:
        raise UserAlreadyExistsException()
    except PyMongoError as exc:
        raise DatabaseException(str(exc))


def login_user(payload):
    _validate_required_fields(payload, ["username", "password"])

    username = _normalize_text(payload["username"])
    password = payload["password"]

    try:
        user = users_col.find_one({"username": username})
        if not user:
            raise UserNotFoundException()

        stored_password_hash = user.get("password_hash", "")
        if not bcrypt.checkpw(
            _normalize_text(password).encode("utf-8"),
            stored_password_hash.encode("utf-8"),
        ):
            raise UnauthorizedException("Invalid credentials")

        token_payload = {
            "user_id": str(user["_id"]),
            "username": user["username"],
            "role": user["role"],
            "session_id": str(uuid4()),
            "device_fingerprint_hash": "",
            "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRY_MINUTES),
        }

        token = jwt.encode(token_payload, JWT_SECRET, algorithm="HS256")
        if isinstance(token, bytes):
            token = token.decode("utf-8")

        return {"token": token, "role": user["role"]}
    except (UserNotFoundException, UnauthorizedException):
        raise
    except ValueError:
        raise UnauthorizedException("Invalid credentials")
    except PyMongoError as exc:
        raise DatabaseException(str(exc))


def get_profile(user_id):
    try:
        user = users_col.find_one({"_id": ObjectId(user_id)})
    except (InvalidId, TypeError):
        raise UserNotFoundException()
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    if not user:
        raise UserNotFoundException()

    return {
        "user_id": str(user["_id"]),
        "username": user["username"],
        "role": user["role"],
        "created_at": _serialize_created_at(user.get("created_at")),
    }


def get_exam_state(exam_id):
    try:
        exam = exams_col.find_one({"_id": ObjectId(exam_id)})
    except (InvalidId, TypeError):
        raise ExamNotFoundException()
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    if not exam:
        raise ExamNotFoundException()

    return {
        "exam_id": str(exam["_id"]),
        "state": exam.get("state"),
    }


def get_health_data():
    return {
        "module_name": ModuleName.AUTH.value,
        "dependencies": ["mongodb"],
        "version": "1.0.0",
        "healthy": True,
    }