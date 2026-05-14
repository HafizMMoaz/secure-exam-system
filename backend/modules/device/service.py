import hashlib
import json

import requests
from pymongo.errors import PyMongoError

from config.config import devices_col, BASE_URL, now
from enums.log_level import LogLevel
from enums.module_name import ModuleName
from exceptions import BadRequestException, DatabaseException, ForbiddenException


REQUIRED_SIGNALS = [
    "user_agent",
    "screen_resolution",
    "timezone",
    "language",
    "platform",
]


def _iso_now():
    return now().replace(microsecond=0).isoformat()


def _serialize_dt(value):
    if value is None:
        return None
    return value.replace(microsecond=0).isoformat()


def _extract_signals(payload):
    payload = payload or {}
    missing = [key for key in REQUIRED_SIGNALS if not payload.get(key)]
    if missing:
        raise BadRequestException(f"Missing required fields: {', '.join(missing)}")

    return {
        "user_agent": str(payload.get("user_agent")),
        "screen_resolution": str(payload.get("screen_resolution")),
        "timezone": str(payload.get("timezone")),
        "language": str(payload.get("language")),
        "platform": str(payload.get("platform")),
    }


def _compute_fingerprint(signals):
    return hashlib.sha256(json.dumps(signals, sort_keys=True).encode()).hexdigest()


def _send_log(level, user_id, action, fingerprint):
    payload = {
        "module": ModuleName.DEVICE.value,
        "level": level,
        "user_id": user_id,
        "exam_id": "",
        "action": action,
        "details": {"fingerprint": fingerprint},
        "timestamp": _iso_now(),
    }
    try:
        requests.post(f"{BASE_URL}/api/logs/write", json=payload, timeout=2)
    except Exception:
        pass


def register_device(user_context, payload):
    """
    PRD section 11 Module 3 - "Device binding, Prevent account sharing".
    First registration for a user binds them to that fingerprint.
    Subsequent registrations from a DIFFERENT fingerprint are rejected
    as suspected account sharing. Matching fingerprint is idempotent.
    """
    user_id = (user_context or {}).get("user_id")
    signals = _extract_signals(payload)
    fingerprint = _compute_fingerprint(signals)

    try:
        existing_match = devices_col.find_one({"user_id": user_id, "fingerprint": fingerprint})
        if existing_match:
            devices_col.update_one(
                {"_id": existing_match.get("_id")},
                {"$set": {"last_seen": now()}},
            )
            return {"fingerprint": fingerprint, "status": "already_registered"}

        existing_any = devices_col.find_one({"user_id": user_id})
        if existing_any:
            # Different fingerprint from the one this user is bound to ->
            # block and log. This is the prevent-account-sharing path.
            _send_log(LogLevel.SECURITY.value, user_id, "device_binding_violation", fingerprint)
            raise ForbiddenException(
                "This account is bound to a different device. Sign in from your original device."
            )

        current = now()
        devices_col.insert_one(
            {
                "user_id": user_id,
                "fingerprint": fingerprint,
                "signals": signals,
                "registered_at": current,
                "is_trusted": True,
                "last_seen": current,
            }
        )
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    _send_log(LogLevel.INFO.value, user_id, "device_registered", fingerprint)
    return {"fingerprint": fingerprint, "status": "registered"}


def verify_device(user_context, payload):
    user_id = (user_context or {}).get("user_id")
    signals = _extract_signals(payload)
    fingerprint = _compute_fingerprint(signals)

    try:
        device = devices_col.find_one({"user_id": user_id, "fingerprint": fingerprint})
        if not device:
            _send_log(LogLevel.SECURITY.value, user_id, "device_mismatch", fingerprint)
            return {"is_trusted": False, "fingerprint": fingerprint}

        devices_col.update_one(
            {"_id": device.get("_id")},
            {"$set": {"last_seen": now()}},
        )
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    _send_log(LogLevel.INFO.value, user_id, "device_verified", fingerprint)
    return {"is_trusted": True, "fingerprint": fingerprint}


def list_devices(user_context):
    user_id = (user_context or {}).get("user_id")

    try:
        cursor = devices_col.find({"user_id": user_id}).sort("registered_at", -1)
        items = []
        for item in cursor:
            items.append(
                {
                    "device_id": str(item.get("_id")),
                    "user_id": item.get("user_id"),
                    "fingerprint": item.get("fingerprint"),
                    "registered_at": _serialize_dt(item.get("registered_at")),
                    "is_trusted": bool(item.get("is_trusted", False)),
                    "last_seen": _serialize_dt(item.get("last_seen")),
                }
            )
        return {"devices": items, "count": len(items)}
    except PyMongoError as exc:
        raise DatabaseException(str(exc))


def get_health():
    return {
        "module_name": ModuleName.DEVICE.value,
        "dependencies": ["mongodb"],
        "version": "1.0.0",
        "healthy": True,
    }
