from flask import request

from responses import success_response, health_response
from modules.randomization.service import (
    generate_randomized_order,
    get_randomized_order,
    get_health,
)


def generate():
    user_context = getattr(request, "user", {})
    payload = request.get_json(silent=True) or {}
    data = generate_randomized_order(user_context, payload)
    return success_response(data=data)


def order():
    user_context = getattr(request, "user", {})
    exam_id = request.args.get("exam_id")
    data = get_randomized_order(user_context, exam_id)
    return success_response(data=data)


def health():
    data = get_health()
    return health_response(**data)
