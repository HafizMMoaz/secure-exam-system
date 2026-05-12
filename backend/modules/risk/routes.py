from flask import Blueprint

from middleware.jwt_auth import jwt_required, role_required
from modules.risk.controller import compute, dashboard, student, health, stream

risk_bp = Blueprint("risk_bp", __name__)


@risk_bp.route("/compute/<exam_id>", methods=["POST"])
@jwt_required
@role_required("teacher")
def compute_route(exam_id):
    """
    Compute risk scores for all students in an exam.
    ---
    tags:
      - Risk
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: exam_id
        type: string
        required: true
    responses:
      200:
        description: Risk computation completed
      400:
        description: Bad request
      403:
        description: Forbidden
    """
    return compute(exam_id)


@risk_bp.route("/dashboard/<exam_id>", methods=["GET"])
@jwt_required
@role_required("teacher")
def dashboard_route(exam_id):
    """
    Return risk dashboard data for an exam.
    ---
    tags:
      - Risk
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: exam_id
        type: string
        required: true
    responses:
      200:
        description: Dashboard returned
    """
    return dashboard(exam_id)


@risk_bp.route("/student/<student_id>", methods=["GET"])
@jwt_required
def student_route(student_id):
    """
    Return an individual student's risk score.
    ---
    tags:
      - Risk
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: student_id
        type: string
        required: true
      - in: query
        name: exam_id
        type: string
        required: true
    responses:
      200:
        description: Student risk returned
      403:
        description: Forbidden
    """
    return student(student_id)


@risk_bp.route("/stream/<exam_id>", methods=["GET"])
@jwt_required
@role_required("teacher")
def stream_route(exam_id):
    """
    Server-Sent Events stream of monitoring events for an exam (§24 bonus).

    Emits tab, clipboard, activity, and behavioral events as they land in
    Mongo. Consume from the frontend via `new EventSource(url)`.
    ---
    tags:
      - Risk
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: exam_id
        type: string
        required: true
    responses:
      200:
        description: SSE stream of monitoring events
    """
    return stream(exam_id)


@risk_bp.route("/health", methods=["GET"])
def health_route():
    """
    Risk module health check.
    ---
    tags:
      - Risk
    security: []
    responses:
      200:
        description: Module health
    """
    return health()
