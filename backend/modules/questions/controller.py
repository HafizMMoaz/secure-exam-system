from flask import request

from exceptions import BadRequestException
from responses import success_response, health_response
from modules.questions.service import (
    approve_exam,
    approve_student,
    enroll_student,
    create_exam,
    create_question,
    delete_exam,
    delete_question,
    get_all_questions_for_student,
    get_exam,
    get_exam_public,
    get_exam_students,
    get_exam_results,
    get_student_answers,
    list_exams,
    list_questions,
    save_answer,
    update_exam,
    update_question,
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
    auth_header = request.headers.get("Authorization", "")
    data = approve_exam(user_context, payload, auth_header)
    return success_response(data=data)


def enroll_student_route():
    user_context = getattr(request, "user", {})
    payload = request.get_json(silent=True) or {}
    exam_id = payload.get("exam_id")
    if not exam_id:
        raise BadRequestException("exam_id is required")
    auth_header = request.headers.get("Authorization", "")
    data = enroll_student(user_context, exam_id, auth_header)
    return success_response(data=data)


def get_exam_public_route(exam_id):
    data = get_exam_public(exam_id)
    return success_response(data=data)


def list_all_for_student_route(exam_id):
    user_context = getattr(request, "user", {})
    data = get_all_questions_for_student(user_context, exam_id)
    return success_response(data=data)


def save_answer_route():
    user_context = getattr(request, "user", {})
    payload = request.get_json(silent=True) or {}
    data = save_answer(user_context, payload)
    return success_response(data=data)


def list_answers_route():
    user_context = getattr(request, "user", {})
    exam_id = request.args.get("exam_id")
    if not exam_id:
        raise BadRequestException("exam_id is required")
    data = get_student_answers(user_context, exam_id)
    return success_response(data=data)


def list_all(exam_id):
    data = list_questions(exam_id)
    return success_response(data=data)


def update_exam_route(exam_id):
    user_context = getattr(request, "user", {})
    payload = request.get_json(silent=True) or {}
    data = update_exam(user_context, exam_id, payload)
    return success_response(data=data)


def delete_exam_route(exam_id):
    user_context = getattr(request, "user", {})
    data = delete_exam(user_context, exam_id)
    return success_response(data=data)


def update_question_route(question_id):
    user_context = getattr(request, "user", {})
    payload = request.get_json(silent=True) or {}
    data = update_question(user_context, question_id, payload)
    return success_response(data=data)


def delete_question_route(question_id):
    user_context = getattr(request, "user", {})
    data = delete_question(user_context, question_id)
    return success_response(data=data)


def approve_student_route():
    user_context = getattr(request, "user", {})
    payload = request.get_json(silent=True) or {}
    data = approve_student(user_context, payload)
    return success_response(data=data)


def get_exam_students_route(exam_id):
    user_context = getattr(request, "user", {})
    data = get_exam_students(user_context, exam_id)
    return success_response(data=data)


def get_exam_results_route(exam_id):
    user_context = getattr(request, "user", {})
    data = get_exam_results(user_context, exam_id)
    return success_response(data=data)


def health():
    data = get_health()
    return health_response(**data)
