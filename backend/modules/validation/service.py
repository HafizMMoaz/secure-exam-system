import requests

from config.config import BASE_URL, now
from enums.module_name import ModuleName
from enums.log_level import LogLevel
from exceptions import BadRequestException


NO_SQL_PATTERNS = [
    "$where",
    "$gt",
    "$lt",
    "$ne",
    "$in",
    "$nin",
    "$or",
    "$and",
    "$regex",
    "$expr",
    "$function",
    "db.",
    "eval(",
    "mapreduce",
]

XSS_PATTERNS = [
    "<script",
    "javascript:",
    "onerror=",
    "onload=",
    "onclick=",
    "alert(",
    "document.cookie",
    "<iframe",
    "<img",
    "src=",
]


def _get_depth(obj, current=0):
    if not isinstance(obj, dict) or current > 5:
        return current
    if not obj:
        return current
    return max(_get_depth(v, current + 1) for v in obj.values())


def _iter_values(obj):
    if isinstance(obj, dict):
        for value in obj.values():
            yield from _iter_values(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _iter_values(item)
    else:
        yield obj


def _scan_string(value):
    text = value if isinstance(value, str) else str(value)
    lower_text = text.lower()
    violations = []

    if len(text) > 2000:
        violations.append("field exceeds maximum length of 2000 characters")

    for pattern in NO_SQL_PATTERNS:
        if pattern in lower_text:
            violations.append(f"NoSQL injection pattern detected: {pattern}")

    for pattern in XSS_PATTERNS:
        if pattern in lower_text:
            violations.append(f"XSS pattern detected: {pattern}")

    return violations


def _collect_violations(data):
    violations = []

    if not isinstance(data, dict):
        return ["input must be a JSON object"]

    if _get_depth(data) > 5:
        violations.append("JSON body nesting depth exceeds 5 levels")

    for value in _iter_values(data):
        if isinstance(value, str):
            violations.extend(_scan_string(value))

    return violations


def validate_input(data: dict) -> tuple[bool, str]:
    """
    Validate a dict of input fields against all security rules.
    Returns (True, "") if valid.
    Returns (False, "reason string") if invalid.
    Other modules import and call this before processing any user input.

    Usage in other services:
        from modules.validation.service import validate_input
        is_valid, reason = validate_input(request.get_json() or {})
        if not is_valid:
            raise BadRequestException(reason)
    """
    violations = _collect_violations(data)
    if violations:
        return False, violations[0]
    return True, ""


def check_input(data):
    violations = _collect_violations(data)
    return {
        "is_valid": not violations,
        "violations": violations,
        "fields_checked": _count_fields(data),
    }


def sanitize_text(text):
    if text is None:
        raise BadRequestException("text is required")

    violations = _scan_string(text)
    return {
        "original": text,
        "is_safe": not violations,
        "violations": violations,
    }


def _count_fields(data):
    if isinstance(data, dict):
        return sum(_count_fields(value) for value in data.values()) or len(data)
    if isinstance(data, list):
        return sum(_count_fields(item) for item in data) or len(data)
    return 1


def _send_security_log(user_id, violations):
    payload = {
        "module": ModuleName.VALIDATION.value,
        "level": LogLevel.SECURITY.value,
        "user_id": user_id or "",
        "exam_id": "",
        "action": "input_validation_failed",
        "details": {"violations": violations},
        "timestamp": now().replace(microsecond=0).isoformat() + "Z",
    }
    try:
        requests.post(f"{BASE_URL}/api/logs/write", json=payload, timeout=2)
    except Exception:
        pass


def log_validation_failure(user_id, violations):
    _send_security_log(user_id, violations)


def get_health():
    return {"module_name": ModuleName.VALIDATION.value, "dependencies": [], "version": "1.0.0", "healthy": True}
