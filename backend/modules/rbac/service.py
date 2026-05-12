import requests
from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import PyMongoError

from config.config import users_col, BASE_URL, now
from enums.log_level import LogLevel
from enums.module_name import ModuleName
from enums.user_role import UserRole
from exceptions import BadRequestException, DatabaseException, UserNotFoundException


PERMISSIONS = {
    "student": [
        "POST /api/session/create",
        "GET /api/session/validate",
        "POST /api/device/register",
        "POST /api/device/verify",
        "POST /api/activation/validate",
        "GET /api/questions/next",
        "POST /api/timer/start",
        "GET /api/timer/status",
        "POST /api/behavioral/event",
        "GET /api/behavioral/risk-data",
        "POST /api/logs/write",
        "GET /api/device/list",
    ],
    "teacher": [
        "POST /api/activation/generate",
        "GET /api/activation/status",
        "GET /api/logs/list",
        "GET /api/logs/verify",
        "GET /api/session/list",
        "GET /api/risk/dashboard",
        "GET /api/similarity/results",
        "POST /api/logs/write",
        "GET /api/device/list",
        "GET /api/session/validate",
    ],
}


def _iso_dt(value):
    if value is None:
        return None
    return value.replace(microsecond=0).isoformat() + "Z"


def _send_log(level, user_id, action, details):
    payload = {
        "module": ModuleName.RBAC.value,
        "level": level,
        "user_id": user_id or "",
        "exam_id": "",
        "action": action,
        "details": details or {},
        "timestamp": _iso_dt(now()),
    }
    try:
        requests.post(f"{BASE_URL}/api/logs/write", json=payload, timeout=2)
    except Exception:
        pass


def get_permissions(user_context):
    role = (user_context or {}).get("role")
    return {
        "role": role,
        "permissions": PERMISSIONS.get(role, []),
    }


def check_access(user_context, payload):
    endpoint = (payload or {}).get("endpoint")
    method = (payload or {}).get("method")

    if not endpoint:
        raise BadRequestException("endpoint is required")
    if not method:
        raise BadRequestException("method is required")

    role = (user_context or {}).get("role")
    key = f"{method.upper()} {str(endpoint).strip()}"
    allowed = key in PERMISSIONS.get(role, [])

    if not allowed:
        _send_log(
            LogLevel.SECURITY.value,
            (user_context or {}).get("user_id"),
            "rbac_access_denied",
            {
                "endpoint": str(endpoint).strip(),
                "method": method.upper(),
                "role": role,
            },
        )

    return {
        "allowed": allowed,
        "role": role,
        "endpoint": str(endpoint).strip(),
        "method": method.upper(),
    }


def list_users(role=None):
    query = {}
    if role is not None:
        normalized = str(role).strip().lower()
        valid_roles = {UserRole.STUDENT.value, UserRole.TEACHER.value}
        if normalized not in valid_roles:
            raise BadRequestException("role must be 'student' or 'teacher'")
        query["role"] = normalized

    try:
        cursor = users_col.find(query).sort("created_at", -1)
        users = []
        for user in cursor:
            users.append(
                {
                    "user_id": str(user.get("_id")),
                    "username": user.get("username"),
                    "role": user.get("role"),
                    "created_at": _iso_dt(user.get("created_at")),
                    "is_active": bool(user.get("is_active", False)),
                }
            )
        return {"users": users, "count": len(users)}
    except PyMongoError as exc:
        raise DatabaseException(str(exc))


def toggle_user_status(user_id, actor_user_id=None):
    try:
        user = users_col.find_one({"_id": ObjectId(user_id)})
    except (InvalidId, TypeError):
        raise UserNotFoundException()
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    if not user:
        raise UserNotFoundException()

    new_value = not bool(user.get("is_active", False))

    # §27.6 (refined): Module 5 owns `is_active` — see ARCHITECTURE.md.
    try:
        users_col.update_one(
            {"_id": user.get("_id")},
            {"$set": {"is_active": new_value}},
        )
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    _send_log(
        LogLevel.INFO.value,
        actor_user_id,
        "user_status_toggled",
        {"user_id": user_id, "is_active": new_value},
    )

    return {"user_id": user_id, "is_active": new_value}


def get_health():
    return {
        "module_name": ModuleName.RBAC.value,
        "dependencies": ["mongodb"],
        "version": "1.0.0",
        "healthy": True,
    }
