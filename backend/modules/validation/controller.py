from flask import request

from responses import success_response, health_response
from modules.validation.service import check_input, sanitize_text, log_validation_failure
from enums.module_name import ModuleName


def check():
    user_context = getattr(request, "user", {})
    payload = request.get_json(silent=True) or {}
    data = check_input(payload)
    if not data["is_valid"]:
        log_validation_failure((user_context or {}).get("user_id"), data["violations"])
    return success_response(data=data)


def sanitize():
    user_context = getattr(request, "user", {})
    payload = request.get_json(silent=True) or {}
    text = payload.get("text")
    data = sanitize_text(text)
    if not data["is_safe"]:
        log_validation_failure((user_context or {}).get("user_id"), data["violations"])
    return success_response(data=data)


def health():
    return health_response(module_name=ModuleName.VALIDATION.value, dependencies=[], version="1.0.0", healthy=True)
