from flask import request

from responses import success_response, health_response
from modules.timer.service import (
    start_exam,
    status,
    submit_exam,
    get_health,
)


def start():
    user_context = getattr(request, "user", {})
    payload = request.get_json(silent=True) or {}
    data = start_exam(user_context, payload)
    return success_response(data=data)


def stat():
    user_context = getattr(request, "user", {})
    exam_id = request.args.get("exam_id")
    data = status(user_context, exam_id)
    return success_response(data=data)


def submit():
    user_context = getattr(request, "user", {})
    payload = request.get_json(silent=True) or {}
    data = submit_exam(user_context, payload)
    return success_response(data=data)


def health():
    data = get_health()
    return health_response(**data)
