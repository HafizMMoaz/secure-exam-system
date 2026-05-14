from config.config import now, iso_utc_z
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
    return iso_utc_z(dt)


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

    # Resolve username NOW and persist on the log doc. Stored outside the
    # integrity-hashed content so the chain isn't affected. This makes the
    # audit log self-contained - historical entries still read correctly
    # after the user is wiped.
    from config.config import users_col
    resolved_username = ""
    if user_id:
        try:
            udoc = users_col.find_one({"_id": ObjectId(user_id)}, {"username": 1})
            if udoc:
                resolved_username = udoc.get("username", "")
        except Exception:
            pass
    if not user_id:
        display_name = "System"
    elif isinstance(user_id, str) and user_id.startswith("system_"):
        display_name = "System"
    else:
        display_name = resolved_username or "Deleted user"

    doc = dict(content)
    doc.update({
        "integrity_hash": integrity_hash,
        "received_at": now(),
        "username": display_name,
    })

    try:
        result = logs_col.insert_one(doc)
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    # section 24 bonus: broadcast every new log to the WebSocket logs room so the
    # teacher audit-log UI updates in real time without polling.
    try:
        from middleware.socketio_app import emit_log_event
        ws_doc = {
            "log_id": str(result.inserted_id),
            "module": module,
            "level": level,
            "user_id": user_id,
            "username": display_name,
            "exam_id": exam_id or "",
            "action": action,
            "details": details,
            "timestamp": timestamp,
            "integrity_hash": integrity_hash,
        }
        emit_log_event(ws_doc)
    except Exception:
        pass

    return str(result.inserted_id)


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


def verify_window(filters):
    """
    Recompute SHA-256 integrity hashes over a window of logs and flag
    any tampered entries. Use it to demonstrate the section 27.3 integrity claim:
    tamper with a log document in Mongo, then call this endpoint and
    see the entry surface as not-intact.

    Accepted query filters: same shape as list_logs (user_id, exam_id,
    level, module) plus an optional `limit` (default 500, max 5000).
    """
    query = {}
    if filters.get("user_id"):
        query["user_id"] = filters.get("user_id")
    if filters.get("exam_id") is not None:
        query["exam_id"] = filters.get("exam_id")
    if filters.get("level"):
        query["level"] = filters.get("level")
    if filters.get("module"):
        query["module"] = filters.get("module")
    if filters.get("action"):
        query["action"] = filters.get("action")

    try:
        limit = int(filters.get("limit") or 500)
    except (TypeError, ValueError):
        raise BadRequestException("limit must be an integer")
    limit = max(1, min(limit, 5000))

    try:
        cursor = logs_col.find(query).sort("received_at", -1).limit(limit)
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    total = 0
    intact = 0
    tampered = []
    for log in cursor:
        total += 1
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
        if computed == stored:
            intact += 1
        else:
            tampered.append({
                "log_id": str(log.get("_id")),
                "module": log.get("module"),
                "action": log.get("action"),
                "timestamp": log.get("timestamp"),
                "stored_hash": stored,
                "computed_hash": computed,
            })

    return {
        "checked": total,
        "intact": intact,
        "tampered_count": len(tampered),
        "tampered": tampered,
        "all_intact": len(tampered) == 0,
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
        cursor = list(logs_col.find(query).sort("received_at", -1))
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    # Batched username resolution so the UI never has to display raw IDs.
    from config.config import users_col
    unique_ids = {log.get("user_id") for log in cursor if log.get("user_id")}
    object_ids = []
    for uid in unique_ids:
        try:
            object_ids.append(ObjectId(uid))
        except Exception:
            pass
    username_map = {}
    if object_ids:
        for udoc in users_col.find({"_id": {"$in": object_ids}}, {"username": 1}):
            username_map[str(udoc["_id"])] = udoc.get("username", "")

    items = []
    for log in cursor:
        uid = log.get("user_id") or ""
        # Prefer the username stored on the log at write time - it survives
        # user deletion. Fall back to live lookup for legacy entries
        # written before this field existed.
        stored_name = log.get("username")
        if stored_name:
            display_name = stored_name
        else:
            display_name = _resolve_username_for_log(uid, username_map)
        items.append({
            "log_id": str(log.get("_id")),
            "module": log.get("module"),
            "level": log.get("level"),
            "user_id": uid,
            "username": display_name,
            "exam_id": log.get("exam_id") or "",
            "action": log.get("action"),
            "details": log.get("details") or {},
            "timestamp": log.get("timestamp"),
            "integrity_hash": log.get("integrity_hash"),
            "received_at": _serialize_dt(log.get("received_at")),
        })

    return {"logs": items, "count": len(items)}


def _resolve_username_for_log(uid, username_map):
    """
    Username display rule for log rows:
      empty/None     -> "System"   (action by the backend, no actor)
      starts "system_" -> "System" (synthetic actor like system_timer)
      in users       -> username
      not in users   -> "Deleted user"  (account was wiped after log was written)
    """
    if not uid:
        return "System"
    if isinstance(uid, str) and uid.startswith("system_"):
        return "System"
    if uid in username_map and username_map[uid]:
        return username_map[uid]
    return "Deleted user"


def get_health():
    return {
        "module_name": ModuleName.LOGGING.value,
        "dependencies": ["mongodb"],
        "version": "1.0.0",
        "healthy": True,
    }
