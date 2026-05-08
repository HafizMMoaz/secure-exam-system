from config.config import now
import hashlib
import json

from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import PyMongoError

from config.config import logs_col
from enums.log_level import LogLevel
from enums.module_name import ModuleName
from exceptions import BadRequestException, DatabaseException, NotFoundException


def _serialize_dt(dt):
    if dt is None:
        return None
    return dt.replace(microsecond=0).isoformat() + "Z"


def _compute_integrity(content_dict):
    try:
        return hashlib.sha256(
            json.dumps(content_dict, sort_keys=True).encode()
        ).hexdigest()
    except (TypeError, ValueError) as exc:
        raise BadRequestException("details must be JSON-serializable")


def write_log(payload):
    # Required fields
    required = ["module", "level", "user_id", "action", "timestamp"]
    missing = [f for f in required if not payload.get(f) and payload.get(f) != "0"]
    if missing:
        raise BadRequestException(f"Missing required fields: {', '.join(missing)}")

    module = payload.get("module")
    level = payload.get("level")
    user_id = payload.get("user_id")
    exam_id = payload.get("exam_id") or ""
    action = payload.get("action")
    details = payload.get("details") if payload.get("details") is not None else {}
    timestamp = payload.get("timestamp")

    # Validate enums
    valid_levels = {lvl.value for lvl in LogLevel}
    if level not in valid_levels:
        raise BadRequestException("Invalid level value")

    valid_modules = {m.value for m in ModuleName}
    if module not in valid_modules:
        raise BadRequestException("Invalid module value")

    if not isinstance(details, dict):
        raise BadRequestException("details must be an object")

    content = {
        "module": module,
        "level": level,
        "user_id": user_id,
        "exam_id": exam_id or "",
        "action": action,
        "details": details,
        "timestamp": timestamp,
    }

    integrity_hash = _compute_integrity(content)

    doc = dict(content)
    doc.update({"integrity_hash": integrity_hash, "received_at": now()})

    try:
        result = logs_col.insert_one(doc)
        return str(result.inserted_id)
    except PyMongoError as exc:
        raise DatabaseException(str(exc))


def verify_log(log_id):
    try:
        log = logs_col.find_one({"_id": ObjectId(log_id)})
    except (InvalidId, TypeError):
        raise NotFoundException("Log entry not found")
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    if not log:
        raise NotFoundException("Log entry not found")

    content = {
        "module": log.get("module"),
        "level": log.get("level"),
        "user_id": log.get("user_id"),
        "exam_id": log.get("exam_id") or "",
        "action": log.get("action"),
        "details": log.get("details") or {},
        "timestamp": log.get("timestamp"),
    }

    computed = _compute_integrity(content)
    stored = log.get("integrity_hash")

    return {
        "log_id": str(log.get("_id")),
        "is_intact": computed == stored,
        "stored_hash": stored,
        "computed_hash": computed,
    }


def list_logs(filters):
    query = {}
    if filters.get("user_id"):
        query["user_id"] = filters.get("user_id")
    if filters.get("exam_id") is not None:
        query["exam_id"] = filters.get("exam_id")
    if filters.get("level"):
        query["level"] = filters.get("level")
    if filters.get("module"):
        query["module"] = filters.get("module")

    try:
        cursor = logs_col.find(query).sort("received_at", -1)
        items = []
        for log in cursor:
            items.append({
                "log_id": str(log.get("_id")),
                "module": log.get("module"),
                "level": log.get("level"),
                "user_id": log.get("user_id"),
                "exam_id": log.get("exam_id") or "",
                "action": log.get("action"),
                "details": log.get("details") or {},
                "timestamp": log.get("timestamp"),
                "integrity_hash": log.get("integrity_hash"),
                "received_at": _serialize_dt(log.get("received_at")),
            })

        return {"logs": items, "count": len(items)}
    except PyMongoError as exc:
        raise DatabaseException(str(exc))


def get_health():
    return {
        "module_name": ModuleName.LOGGING.value,
        "dependencies": ["mongodb"],
        "version": "1.0.0",
        "healthy": True,
    }
