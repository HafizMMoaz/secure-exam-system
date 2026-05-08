from datetime import datetime, timedelta
import requests

from config.config import sessions_col, JWT_EXPIRY_MINUTES
from enums.module_name import ModuleName
from enums.log_level import LogLevel
from exceptions import (
    SessionAlreadyActiveException,
    SessionNotFoundException,
    DatabaseException,
    UnauthorizedException,
)


def _iso_now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def create_session(user_context):
    session_id = user_context.get("session_id")
    user_id = user_context.get("user_id")
    username = user_context.get("username")
    role = user_context.get("role")

    if not session_id or not user_id:
        raise SessionNotFoundException()

    # Check already active
    existing = sessions_col.find_one({"session_id": session_id, "is_active": True})
    if existing:
        raise SessionAlreadyActiveException()

    now = datetime.utcnow()
    expires_at = now + timedelta(minutes=JWT_EXPIRY_MINUTES)

    doc = {
        "session_id": session_id,
        "user_id": user_id,
        "username": username,
        "role": role,
        "created_at": now,
        "expires_at": expires_at,
        "is_active": True,
        "invalidated_at": None,
    }

    try:
        result = sessions_col.insert_one(doc)
    except Exception as exc:
        raise DatabaseException(str(exc))

    # Send log via HTTP POST to logging endpoint (best-effort)
    log_payload = {
        "module": ModuleName.SESSION.value,
        "level": LogLevel.INFO.value,
        "user_id": user_id,
        "exam_id": "",
        "action": "session_created",
        "details": {"session_id": session_id},
        "timestamp": _iso_now(),
    }
    try:
        requests.post("http://localhost:5000/api/logs/write", json=log_payload, timeout=2)
    except Exception:
        pass

    return {"session_id": session_id}


def invalidate_session(session_id):
    session = sessions_col.find_one({"session_id": session_id})
    if not session:
        raise SessionNotFoundException()

    try:
        sessions_col.update_one(
            {"session_id": session_id},
            {"$set": {"is_active": False, "invalidated_at": datetime.utcnow()}},
        )
    except Exception as exc:
        raise DatabaseException(str(exc))

    # Log
    try:
        requests.post(
            "http://localhost:5000/api/logs/write",
            json={
                "module": ModuleName.SESSION.value,
                "level": LogLevel.INFO.value,
                "user_id": session.get("user_id"),
                "exam_id": "",
                "action": "session_invalidated",
                "details": {"session_id": session_id},
                "timestamp": _iso_now(),
            },
            timeout=2,
        )
    except Exception:
        pass

    return {"message": "Session invalidated"}


def validate_session(session_id):
    session = sessions_col.find_one({"session_id": session_id})
    if not session:
        raise SessionNotFoundException()

    now = datetime.utcnow()
    expires_at = session.get("expires_at")
    is_active = session.get("is_active", False)

    if not is_active or (expires_at and expires_at < now):
        raise UnauthorizedException("Session is no longer valid")

    return {
        "session_id": session.get("session_id"),
        "user_id": session.get("user_id"),
        "is_active": session.get("is_active"),
        "expires_at": session.get("expires_at").replace(microsecond=0).isoformat() + "Z",
    }


def list_sessions(user_id=None):
    query = {}
    if user_id:
        query["user_id"] = user_id

    try:
        cursor = sessions_col.find(query).sort("created_at", -1)
        items = []
        for s in cursor:
            items.append({
                "session_id": s.get("session_id"),
                "user_id": s.get("user_id"),
                "username": s.get("username"),
                "role": s.get("role"),
                "created_at": s.get("created_at").replace(microsecond=0).isoformat() + "Z" if s.get("created_at") else None,
                "expires_at": s.get("expires_at").replace(microsecond=0).isoformat() + "Z" if s.get("expires_at") else None,
                "is_active": s.get("is_active", False),
                "invalidated_at": s.get("invalidated_at").replace(microsecond=0).isoformat() + "Z" if s.get("invalidated_at") else None,
            })
        return {"sessions": items, "count": len(items)}
    except Exception as exc:
        raise DatabaseException(str(exc))


def get_health():
    return {
        "module_name": ModuleName.SESSION.value,
        "dependencies": ["mongodb"],
        "version": "1.0.0",
        "healthy": True,
    }
