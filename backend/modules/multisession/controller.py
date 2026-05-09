from flask import request

from responses import success_response, health_response, risk_data_response
from enums.module_name import ModuleName
from modules.multisession.service import detect_multi_session, get_history, get_risk_data, get_health


def detect():
    user_context = getattr(request, "user", {})
    data = detect_multi_session(user_context)
    return success_response(data=data)


def history():
    user_context = getattr(request, "user", {})
    requested_user_id = request.args.get("user_id")
    data = get_history(user_context, requested_user_id=requested_user_id)
    return success_response(data=data)


def risk_data():
    user_id = request.args.get("user_id")
    exam_id = request.args.get("exam_id")
    data = get_risk_data(user_id, exam_id)
    return risk_data_response(module_name=ModuleName.MULTISESSION.value, data=data)


def health():
    data = get_health()
    return health_response(**data)
