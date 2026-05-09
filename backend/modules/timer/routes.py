from flask import Blueprint

from middleware.jwt_auth import jwt_required, role_required
from modules.timer.controller import start, stat, submit, health

timer_bp = Blueprint("timer_bp", __name__)


@timer_bp.route("/start", methods=["POST"])
@jwt_required
@role_required("student")
def start_route():
    """
    Start an exam session (server-side timer).
    ---
    tags:
      - Timer
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
        description: Exam started
      400:
        description: Bad request
    """
    return start()


@timer_bp.route("/status", methods=["GET"])
@jwt_required
@role_required("student")
def status_route():
    """
    Get current exam timer status for the authenticated student.
    ---
    tags:
      - Timer
    security:
      - BearerAuth: []
    parameters:
      - in: query
        name: exam_id
        type: string
        required: true
    responses:
      200:
        description: Timer status
      404:
        description: Not found
    """
    return stat()


@timer_bp.route("/submit", methods=["POST"])
@jwt_required
@role_required("student")
def submit_route():
    """
    Submit the exam (finalize session) if within allowed time.
    ---
    tags:
      - Timer
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
        description: Exam submitted
      400:
        description: Bad request or time expired
    """
    return submit()


@timer_bp.route("/health", methods=["GET"])
def health_route():
    """
    Timer module health check.
    ---
    tags:
      - Timer
    security: []
    responses:
      200:
        description: Module health
    """
    return health()
