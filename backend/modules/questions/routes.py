from flask import Blueprint

from middleware.jwt_auth import jwt_required, role_required
from modules.questions.controller import (
  approve_exam_route,
  create,
  create_exam_route,
  get_exam_route,
  list_all,
  list_exams_route,
  next_q,
  health,
)

questions_bp = Blueprint("questions_bp", __name__)


@questions_bp.route("/create", methods=["POST"])
@jwt_required
@role_required("teacher")
def create_route():
    """
    Create a question for an exam (teacher only).
    ---
    tags:
      - Questions
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - exam_id
            - text
            - options
            - correct_answer
          properties:
            exam_id:
              type: string
            text:
              type: string
            options:
              type: array
              items:
                type: string
            correct_answer:
              type: string
            marks:
              type: integer
    responses:
      200:
        description: Question created
      400:
        description: Bad request
    """
    return create()


@questions_bp.route("/next", methods=["GET"])
@jwt_required
@role_required("student")
def next_route():
    """
    Get the next unanswered question for the authenticated student.
    ---
    tags:
      - Questions
    security:
      - BearerAuth: []
    parameters:
      - in: query
        name: exam_id
        type: string
        required: true
    responses:
      200:
        description: Next question returned
      401:
        description: Invalid or missing JWT
      403:
        description: Exam not in progress
    """
    return next_q()


@questions_bp.route("/list/<exam_id>", methods=["GET"])
@jwt_required
@role_required("teacher")
def list_route(exam_id):
    """
    List all questions for an exam (teacher only).
    ---
    tags:
      - Questions
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: exam_id
        type: string
        required: true
    responses:
      200:
        description: Questions listed
      401:
        description: Invalid or missing JWT
      403:
        description: Insufficient permissions
    """
    return list_all(exam_id)


@questions_bp.route("/health", methods=["GET"])
def health_route():
    """
    Questions module health check.
    ---
    tags:
      - Questions
    security: []
    responses:
      200:
        description: Module health
    """
    return health()


@questions_bp.route("/exams/create", methods=["POST"])
@jwt_required
@role_required("teacher")
def create_exam_bp_route():
    """
    Create a new exam.
    ---
    tags:
      - Questions
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - title
            - duration_minutes
          properties:
            title:
              type: string
            description:
              type: string
            duration_minutes:
              type: integer
              minimum: 10
              maximum: 180
    responses:
      200:
        description: Exam created
      400:
        description: Bad request
      401:
        description: Invalid or missing JWT
      403:
        description: Insufficient permissions
    """
    return create_exam_route()


@questions_bp.route("/exams/list", methods=["GET"])
@jwt_required
@role_required("teacher")
def exams_list_bp_route():
    """
    List exams created by the authenticated teacher.
    ---
    tags:
      - Questions
    security:
      - BearerAuth: []
    responses:
      200:
        description: Exams listed
      401:
        description: Invalid or missing JWT
      403:
        description: Insufficient permissions
    """
    return list_exams_route()


@questions_bp.route("/exams/<exam_id>", methods=["GET"])
@jwt_required
def exam_detail_bp_route(exam_id):
    """
    Get full exam details.
    ---
    tags:
      - Questions
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: exam_id
        type: string
        required: true
    responses:
      200:
        description: Exam returned
      401:
        description: Invalid or missing JWT
      404:
        description: Exam not found
    """
    return get_exam_route(exam_id)


@questions_bp.route("/exams/approve", methods=["POST"])
@jwt_required
@role_required("teacher")
def approve_exam_bp_route():
    """
    Approve an exam for activation.
    ---
    tags:
      - Questions
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - exam_id
          properties:
            exam_id:
              type: string
    responses:
      200:
        description: Exam approved
      400:
        description: Bad request
      401:
        description: Invalid or missing JWT
      403:
        description: Forbidden
      404:
        description: Exam not found
      409:
        description: Invalid exam state
    """
    return approve_exam_route()
