from flask import request

from responses import success_response, health_response, risk_data_response
from enums.module_name import ModuleName
from modules.similarity.service import (
    analyze_exam_similarity,
    get_latest_results,
    get_risk_data,
    get_health,
)


def analyze(exam_id):
    user_context = getattr(request, "user", {})
    data = analyze_exam_similarity(user_context, exam_id)
    return success_response(data=data)


def results(exam_id):
    user_context = getattr(request, "user", {})
    data = get_latest_results(user_context, exam_id)
    return success_response(data=data)


def risk_data():
    user_id = request.args.get("user_id")
    exam_id = request.args.get("exam_id")
    data = get_risk_data(user_id, exam_id)
    return risk_data_response(module_name=ModuleName.SIMILARITY.value, data=data)


def health():
    data = get_health()
    return health_response(**data)
