from flask import request

from responses import health_response, success_response

from modules.auth.service import (
    get_exam_state,
    get_health,
    get_profile,
    login_user,
    register_user,
    request_otp,
    set_exam_state,
    set_user_active,
    verify_otp,
)


def register():
    payload = request.get_json(silent=True) or {}
    data = register_user(payload)
    return success_response(data=data, message="")


def login():
    payload = request.get_json(silent=True) or {}
    data = login_user(payload)
    return success_response(data=data, message="")


def otp_request_action():
    payload = request.get_json(silent=True) or {}
    data = request_otp(payload)
    return success_response(data=data, message="OTP issued")


def otp_verify_action():
    payload = request.get_json(silent=True) or {}
    data = verify_otp(payload)
    return success_response(data=data, message="OTP verified")


def profile():
    user_context = getattr(request, "user", {})
    data = get_profile(user_context.get("user_id"))
    return success_response(data=data, message="")


def exam_state(exam_id):
    data = get_exam_state(exam_id)
    return success_response(data=data, message="")


def exam_state_transition(exam_id):
    user_context = getattr(request, "user", {})
    payload = request.get_json(silent=True) or {}
    data = set_exam_state(user_context, exam_id, payload)
    return success_response(data=data, message="State transitioned")


def user_active_toggle(user_id):
    actor_context = getattr(request, "user", {})
    payload = request.get_json(silent=True) or {}
    data = set_user_active(actor_context, user_id, payload)
    return success_response(data=data, message="User active flag updated")


def health():
    data = get_health()
    return health_response(**data)