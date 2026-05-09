from flask import request

from responses import success_response, health_response, risk_data_response
from enums.module_name import ModuleName
from modules.behavioral.service import (
    record_event,
    analyze_student_behavior,
    get_summary,
    get_risk_data,
    get_health,
)


def event():
    user_context = getattr(request, "user", {})
    payload = request.get_json(silent=True) or {}
    data = record_event(user_context, payload)
    return success_response(data=data)


def analyze():
    user_context = getattr(request, "user", {})
    exam_id = request.args.get("exam_id")
    requested_user_id = request.args.get("user_id")
    data = analyze_student_behavior(user_context, requested_user_id, exam_id)
    return success_response(data=data)


def summary():
    user_context = getattr(request, "user", {})
    exam_id = request.args.get("exam_id")
    requested_user_id = request.args.get("user_id")
    data = get_summary(user_context, exam_id, requested_user_id=requested_user_id)
    return success_response(data=data)


def risk_data():
    user_id = request.args.get("user_id")
    exam_id = request.args.get("exam_id")
    data = get_risk_data(user_id, exam_id)
    return risk_data_response(module_name=ModuleName.BEHAVIORAL.value, data=data)


def health():
    data = get_health()
    return health_response(**data)
