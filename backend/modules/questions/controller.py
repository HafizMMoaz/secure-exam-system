from flask import request

from exceptions import BadRequestException
from responses import success_response, health_response
from modules.questions.service import (
    approve_exam,
    enroll_student,
    create_exam,
    create_question,
    get_exam,
    get_exam_public,
    next_question,
    list_exams,
    list_questions,
    get_health,
)


def create():
    user_context = getattr(request, "user", {})
    payload = request.get_json(silent=True) or {}
    data = create_question(user_context, payload)
    return success_response(data=data)


def create_exam_route():
    user_context = getattr(request, "user", {})
    payload = request.get_json(silent=True) or {}
    data = create_exam(user_context, payload)
    return success_response(data=data)


def list_exams_route():
    user_context = getattr(request, "user", {})
    data = list_exams(user_context)
    return success_response(data=data)


def get_exam_route(exam_id):
    data = get_exam(exam_id)
    return success_response(data=data)


def approve_exam_route():
    user_context = getattr(request, "user", {})
    payload = request.get_json(silent=True) or {}
    data = approve_exam(user_context, payload)
    return success_response(data=data)


def enroll_student_route():
    user_context = getattr(request, "user", {})
    payload = request.get_json(silent=True) or {}
    exam_id = payload.get("exam_id")
    if not exam_id:
        raise BadRequestException("exam_id is required")
    data = enroll_student(user_context, exam_id)
    return success_response(data=data)


def get_exam_public_route(exam_id):
    data = get_exam_public(exam_id)
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
