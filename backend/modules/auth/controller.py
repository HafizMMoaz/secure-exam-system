from flask import request

from responses import health_response, success_response

from modules.auth.service import (
    get_exam_state,
    get_health_data,
    get_profile,
    login_user,
    register_user,
)


def register():
    payload = request.get_json(silent=True) or {}
    data = register_user(payload)
    return success_response(data=data, message="")


def login():
    payload = request.get_json(silent=True) or {}
    data = login_user(payload)
    return success_response(data=data, message="")


def profile():
    user_context = getattr(request, "user", {})
    data = get_profile(user_context.get("user_id"))
    return success_response(data=data, message="")


def exam_state(exam_id):
    data = get_exam_state(exam_id)
    return success_response(data=data, message="")


def health():
    data = get_health_data()
    return health_response(**data)