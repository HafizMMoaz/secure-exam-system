"""
@validate_body decorator (Phase 5.5, Module 9 integration).

Routes wrapped with this decorator call validation/service.validate_input on
the request body before the handler runs. Failed validation raises 400 and
emits a SECURITY log through the §27.3 logging gateway.

Applied conservatively to auth endpoints (small structured bodies, low
risk of false positives). Answer-save and other long-form text endpoints
are intentionally NOT wrapped to avoid blocking legitimate user content
that contains keywords like `<img` or `src=` — Module 9 errs on the side
of paranoid pattern matching, which is appropriate for credentials and
identity fields but not for free-form text.
"""

from functools import wraps

import requests
from flask import request

from config.config import BASE_URL, now
from enums.log_level import LogLevel
from enums.module_name import ModuleName
from exceptions import BadRequestException
from modules.validation.service import validate_input


def _send_validation_log(reason, path):
    payload = {
        "module": ModuleName.VALIDATION.value,
        "level": LogLevel.SECURITY.value,
        "user_id": "",
        "exam_id": "",
        "action": "input_validation_failed",
        "details": {"reason": reason, "path": path},
        "timestamp": now().replace(microsecond=0).isoformat() + "Z",
    }
    try:
        requests.post(f"{BASE_URL}/api/logs/write", json=payload, timeout=2)
    except Exception:
        pass


def validate_body(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            _send_validation_log("body must be a JSON object", request.path)
            raise BadRequestException("Body must be a JSON object")

        is_valid, reason = validate_input(payload)
        if not is_valid:
            _send_validation_log(reason, request.path)
            raise BadRequestException(reason)

        return fn(*args, **kwargs)

    return wrapper
