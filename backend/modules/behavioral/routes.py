from flask import Blueprint

from middleware.jwt_auth import jwt_required, role_required
from modules.behavioral.controller import event, analyze, summary, risk_data, health

behavioral_bp = Blueprint("behavioral_bp", __name__)


@behavioral_bp.route("/event", methods=["POST"])
@jwt_required
@role_required("student")
def event_route():
    """
    Record a behavioral event for a student during an exam.
    ---
    tags:
      - Behavioral
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
            - question_id
            - answer_time_seconds
            - submission_time_seconds
          properties:
            exam_id:
              type: string
            question_id:
              type: string
            answer_time_seconds:
              type: number
            submission_time_seconds:
              type: number
            edit_count:
              type: integer
            answer:
              type: string
    responses:
      200:
        description: Event recorded
      400:
        description: Bad request
    """
    return event()


@behavioral_bp.route("/analyze", methods=["POST"])
@jwt_required
def analyze_route():
    """
    Analyze behavioral events for a student and persist the analysis result.
    ---
    tags:
      - Behavioral
    security:
      - BearerAuth: []
    parameters:
      - in: query
        name: exam_id
        type: string
        required: true
      - in: query
        name: user_id
        type: string
        required: false
    responses:
      200:
        description: Analysis completed
      403:
        description: Forbidden
    """
    return analyze()


@behavioral_bp.route("/summary", methods=["GET"])
@jwt_required
def summary_route():
    """
    Return the latest behavioral analysis summary for a student.
    ---
    tags:
      - Behavioral
    security:
      - BearerAuth: []
    parameters:
      - in: query
        name: exam_id
        type: string
        required: true
      - in: query
        name: user_id
        type: string
        required: false
    responses:
      200:
        description: Summary returned
    """
    return summary()


@behavioral_bp.route("/risk-data", methods=["GET"])
@jwt_required
def risk_data_route():
    """
    Return behavioral risk data for aggregation.
    ---
    tags:
      - Behavioral
    security:
      - BearerAuth: []
    parameters:
      - in: query
        name: user_id
        type: string
        required: true
      - in: query
        name: exam_id
        type: string
        required: true
    responses:
      200:
        description: Risk data returned
    """
    return risk_data()


@behavioral_bp.route("/health", methods=["GET"])
def health_route():
    """
    Behavioral module health check.
    ---
    tags:
      - Behavioral
    security: []
    responses:
      200:
        description: Module health
    """
    return health()
