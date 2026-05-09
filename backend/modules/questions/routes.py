from flask import Blueprint

from middleware.jwt_auth import jwt_required, role_required
from modules.questions.controller import create, next_q, list_all, health

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
