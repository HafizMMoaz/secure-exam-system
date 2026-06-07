import secrets
from datetime import timedelta
from config.config import now, iso_utc_z
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
        return iso_utc_z(created_at)
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

    # Password policy enforcement
    pwd = _normalize_text(password)
    errors = []
    if len(pwd) < 8:
        errors.append("password must be at least 8 characters")
    if not any(c.isupper() for c in pwd):
        errors.append("password must contain an uppercase letter")
    if not any(c.islower() for c in pwd):
        errors.append("password must contain a lowercase letter")
    if not any(c.isdigit() for c in pwd):
        errors.append("password must contain a digit")
    if not any(not c.isalnum() for c in pwd):
        errors.append("password must contain a special character")
    if errors:
        raise BadRequestException("Invalid password: " + "; ".join(errors))

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


def get_exam_state(exam_id, requester_id=None):
    try:
        exam = exams_col.find_one({"_id": ObjectId(exam_id)})
    except (InvalidId, TypeError):
        raise ExamNotFoundException()
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    if not exam:
        raise ExamNotFoundException()

    result = {
        "exam_id": str(exam["_id"]),
        "state": exam.get("state"),
        "approval_mode": exam.get("approval_mode", "both"),
    }
    # If a student is asking, include their own enrollment status so the
    # waiting screen can route them at the right moment without exposing
    # other students' data.
    if requester_id:
        entry = next(
            (s for s in (exam.get("students") or []) if s.get("student_id") == requester_id),
            None,
        )
        if entry is not None:
            result["student_enrolled"] = True
            result["student_approved"] = bool(entry.get("approved"))
            result["student_activated"] = entry.get("activated_at") is not None
    return result


def set_exam_state(user_context, exam_id, payload):
    """
    PRD section 27.6 strict path: Module 1 is the sole writer of exams_col.state.
    Every other module performs state transitions by POSTing here. Module 1
    validates that the requested transition is allowed by the section 27.4 state
    machine (immediate-next-step rule, except idempotent same-state writes
    which are accepted but no-op).
    """
    from enums.exam_state import ExamState

    target = (payload or {}).get("to")
    if not target:
        raise BadRequestException("Field 'to' is required")

    try:
        target_enum = ExamState(target)
    except ValueError:
        raise BadRequestException(f"Unknown target state: {target}")

    try:
        exam = exams_col.find_one({"_id": ObjectId(exam_id)})
    except (InvalidId, TypeError):
        raise ExamNotFoundException()
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    if not exam:
        raise ExamNotFoundException()

    current_value = exam.get("state")
    if current_value == target:
        return {"exam_id": str(exam["_id"]),
                "previous_state": current_value,
                "state": current_value,
                "transitioned": False}

    try:
        current_enum = ExamState(current_value)
    except (ValueError, TypeError):
        raise BadRequestException(f"Exam is in an unrecognized state: {current_value}")

    if not current_enum.can_transition_to(target_enum):
        from exceptions import ExamStateException
        raise ExamStateException(
            current_state=current_value,
            required_state=f"a state preceding {target}",
        )

    try:
        exams_col.update_one(
            {"_id": exam["_id"]},
            {"$set": {"state": target}},
        )
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    actor_module = (payload or {}).get("actor_module") or "unknown"
    _send_state_log(
        user_context,
        str(exam["_id"]),
        current_value,
        target,
        actor_module,
    )

    return {
        "exam_id": str(exam["_id"]),
        "previous_state": current_value,
        "state": target,
        "transitioned": True,
    }


def _send_state_log(user_context, exam_id, prev, target, actor_module):
    payload = {
        "module": ModuleName.AUTH.value,
        "level": LogLevel.INFO.value,
        "user_id": (user_context or {}).get("user_id") or "",
        "exam_id": exam_id,
        "action": "exam_state_transition",
        "details": {"from": prev, "to": target, "actor_module": actor_module},
        "timestamp": iso_utc_z(),
    }
    try:
        requests.post(f"{BASE_URL}/api/logs/write", json=payload, timeout=2)
    except Exception:
        pass


def set_user_active(actor_context, user_id, payload):
    """
    PRD section 27.6 strict path: Module 1 is the sole writer of users_col fields,
    including is_active. Module 5 (RBAC) is the policy authority - it
    decides who gets toggled - and calls this endpoint to actually mutate.
    """
    if (actor_context or {}).get("role") != "teacher":
        from exceptions import ForbiddenException
        raise ForbiddenException("Only teachers can change account status")

    if "is_active" not in (payload or {}):
        raise BadRequestException("Field 'is_active' is required")

    new_value = bool(payload["is_active"])

    try:
        result = users_col.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"is_active": new_value}},
        )
    except (InvalidId, TypeError):
        raise UserNotFoundException()
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    if result.matched_count == 0:
        raise UserNotFoundException()

    payload_log = {
        "module": ModuleName.AUTH.value,
        "level": LogLevel.SECURITY.value,
        "user_id": (actor_context or {}).get("user_id") or "",
        "exam_id": "",
        "action": "user_active_toggled",
        "details": {"target_user_id": user_id, "is_active": new_value},
        "timestamp": iso_utc_z(),
    }
    try:
        requests.post(f"{BASE_URL}/api/logs/write", json=payload_log, timeout=2)
    except Exception:
        pass

    return {"user_id": user_id, "is_active": new_value}


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
    OTP delivery channel for dev: emit the code through the section 27.3 logging
    gateway. A real deployment would replace this with SMS or email.
    """
    payload = {
        "module": ModuleName.AUTH.value,
        "level": (level or LogLevel.SECURITY.value),
        "user_id": user_id or "",
        "exam_id": "",
        "action": action,
        "details": details or {},
        "timestamp": iso_utc_z(),
    }
    try:
        requests.post(f"{BASE_URL}/api/logs/write", json=payload, timeout=2)
    except Exception:
        pass


def request_otp(payload):
    """
    Step 1 of MFA (PRD section 11 Module 1). Verify credentials, generate a
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