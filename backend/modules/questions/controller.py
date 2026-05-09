from flask import request

from responses import success_response, health_response
from modules.questions.service import (
    create_question,
    next_question,
    list_questions,
    get_health,
)


def create():
    user_context = getattr(request, "user", {})
    payload = request.get_json(silent=True) or {}
    data = create_question(user_context, payload)
    return success_response(data=data)


def next_q():
    user_context = getattr(request, "user", {})
    exam_id = request.args.get("exam_id")
    data = next_question(user_context, exam_id)
    return success_response(data=data)


def list_all(exam_id):
    data = list_questions(exam_id)
    return success_response(data=data)


def health():
    data = get_health()
    return health_response(**data)
