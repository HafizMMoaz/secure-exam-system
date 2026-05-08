from flask import request

from responses import success_response, health_response
from modules.activation.service import (
    generate_activation_code,
    validate_activation_code,
    get_activation_status,
    get_health,
)


def generate():
    user_context = getattr(request, "user", {})
    payload = request.get_json(silent=True) or {}
    data = generate_activation_code(user_context, payload)
    return success_response(data=data)


def validate():
    user_context = getattr(request, "user", {})
    payload = request.get_json(silent=True) or {}
    data = validate_activation_code(user_context, payload)
    return success_response(data=data)


def status(exam_id):
    data = get_activation_status(exam_id)
    return success_response(data=data)


def health():
    data = get_health()
    return health_response(**data)
