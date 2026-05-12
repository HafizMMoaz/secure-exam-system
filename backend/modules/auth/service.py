import secrets
from datetime import timedelta
from config.config import now
from uuid import uuid4

import bcrypt
import jwt
import requests
from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import DuplicateKeyError, PyMongoError

from config.config import (
    BASE_URL,
    JWT_SECRET,
    JWT_EXPIRY_MINUTES,
    users_col,
    exams_col,
    otp_codes_col,
)
from enums.user_role import UserRole
from enums.module_name import ModuleName
from enums.log_level import LogLevel
from exceptions import (
    BadRequestException,
    DatabaseException,
    ExamNotFoundException,
    UnauthorizedException,
    UserAlreadyExistsException,
    UserNotFoundException,
)


OTP_TTL_MINUTES = 5
OTP_MAX_ATTEMPTS = 5


def _validate_required_fields(payload, required_fields):
    missing_fields = [field for field in required_fields if not payload.get(field)]
    if missing_fields:
        raise BadRequestException(
            f"Missing required fields: {', '.join(missing_fields)}"
        )


def _serialize_created_at(created_at):
    if isinstance(created_at, type(now())):
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
            "created_at": now(),
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

        return {"token": _issue_token(user), "role": user["role"], "username": user["username"]}
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


def _issue_token(user):
    token_payload = {
        "user_id": str(user["_id"]),
        "username": user["username"],
        "role": user["role"],
        "session_id": str(uuid4()),
        "device_fingerprint_hash": "",
        "exp": now() + timedelta(minutes=JWT_EXPIRY_MINUTES),
    }
    token = jwt.encode(token_payload, JWT_SECRET, algorithm="HS256")
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def _emit_otp_log(user_id, action, details, level=None):
    """
    OTP delivery channel for dev: emit the code through the §27.3 logging
    gateway. A real deployment would replace this with SMS or email.
    """
    payload = {
        "module": ModuleName.AUTH.value,
        "level": (level or LogLevel.SECURITY.value),
        "user_id": user_id or "",
        "exam_id": "",
        "action": action,
        "details": details or {},
        "timestamp": now().replace(microsecond=0).isoformat() + "Z",
    }
    try:
        requests.post(f"{BASE_URL}/api/logs/write", json=payload, timeout=2)
    except Exception:
        pass


def request_otp(payload):
    """
    Step 1 of MFA (PRD §11 Module 1). Verify credentials, generate a
    6-digit OTP, store its hash with a 5-minute TTL, and emit the code
    through the logging gateway for dev-mode delivery. The plaintext
    code is *not* returned in the response.
    """
    _validate_required_fields(payload, ["username", "password"])

    username = _normalize_text(payload["username"])
    password = payload["password"]

    try:
        user = users_col.find_one({"username": username})
        if not user:
            raise UnauthorizedException("Invalid credentials")

        if not bcrypt.checkpw(
            _normalize_text(password).encode("utf-8"),
            user.get("password_hash", "").encode("utf-8"),
        ):
            raise UnauthorizedException("Invalid credentials")

        code = f"{secrets.randbelow(1_000_000):06d}"
        code_hash = bcrypt.hashpw(code.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        otp_codes_col.update_many(
            {"user_id": str(user["_id"]), "used_at": None},
            {"$set": {"used_at": now(), "invalidated_reason": "superseded"}},
        )
        otp_codes_col.insert_one({
            "user_id": str(user["_id"]),
            "username": user["username"],
            "code_hash": code_hash,
            "attempts": 0,
            "created_at": now(),
            "expires_at": now() + timedelta(minutes=OTP_TTL_MINUTES),
            "used_at": None,
        })

        _emit_otp_log(
            str(user["_id"]),
            "otp_issued",
            {"username": user["username"], "code": code, "channel": "dev_log_gateway"},
        )

        return {
            "otp_sent": True,
            "ttl_minutes": OTP_TTL_MINUTES,
            "delivery": "dev_log_gateway",
        }
    except (UnauthorizedException, UserNotFoundException):
        raise
    except PyMongoError as exc:
        raise DatabaseException(str(exc))


def verify_otp(payload):
    """
    Step 2 of MFA: validate the OTP and issue the JWT. After this point
    the JWT is the same shape login() returns.
    """
    _validate_required_fields(payload, ["username", "code"])

    username = _normalize_text(payload["username"])
    code = _normalize_text(payload["code"])

    try:
        user = users_col.find_one({"username": username})
        if not user:
            raise UnauthorizedException("Invalid credentials")

        record = otp_codes_col.find_one(
            {"user_id": str(user["_id"]), "used_at": None},
            sort=[("created_at", -1)],
        )
        if not record:
            raise UnauthorizedException("No active OTP for this user")

        expires_at = record.get("expires_at")
        # pymongo strips tzinfo on read and stores UTC; normalize both sides
        # to UTC-aware before comparing.
        import datetime as _dt
        current_utc = now().astimezone(_dt.timezone.utc)
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=_dt.timezone.utc)
        if expires_at and expires_at < current_utc:
            otp_codes_col.update_one(
                {"_id": record["_id"]},
                {"$set": {"used_at": now(), "invalidated_reason": "expired"}},
            )
            _emit_otp_log(str(user["_id"]), "otp_expired", {"username": username})
            raise UnauthorizedException("OTP expired")

        attempts = int(record.get("attempts") or 0)
        if attempts >= OTP_MAX_ATTEMPTS:
            otp_codes_col.update_one(
                {"_id": record["_id"]},
                {"$set": {"used_at": now(), "invalidated_reason": "max_attempts"}},
            )
            _emit_otp_log(str(user["_id"]), "otp_max_attempts", {"username": username})
            raise UnauthorizedException("OTP attempt limit exceeded")

        if not bcrypt.checkpw(code.encode("utf-8"), record["code_hash"].encode("utf-8")):
            otp_codes_col.update_one(
                {"_id": record["_id"]},
                {"$inc": {"attempts": 1}},
            )
            _emit_otp_log(str(user["_id"]), "otp_bad_code", {"username": username, "attempt": attempts + 1})
            raise UnauthorizedException("Invalid OTP code")

        otp_codes_col.update_one(
            {"_id": record["_id"]},
            {"$set": {"used_at": now(), "invalidated_reason": "consumed"}},
        )

        token = _issue_token(user)
        _emit_otp_log(str(user["_id"]), "otp_consumed", {"username": username}, level=LogLevel.INFO.value)
        return {"token": token, "role": user["role"], "username": user["username"]}
    except (UnauthorizedException, UserNotFoundException):
        raise
    except ValueError:
        raise UnauthorizedException("Invalid credentials")
    except PyMongoError as exc:
        raise DatabaseException(str(exc))


def get_health():
    return {
        "module_name": ModuleName.AUTH.value,
        "dependencies": ["mongodb"],
        "version": "1.0.0",
        "healthy": True,
    }