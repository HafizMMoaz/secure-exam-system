from flask import Blueprint

from middleware.jwt_auth import jwt_required, role_required
from modules.clipboard.controller import event, summary, risk_data, health

clipboard_bp = Blueprint("clipboard_bp", __name__)


@clipboard_bp.route("/event", methods=["POST"])
@jwt_required
@role_required("student")
def event_route():
    """
    Record a clipboard copy, cut, or paste event.
    ---
    tags:
      - Clipboard
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
            - event_type
            - timestamp
          properties:
            exam_id:
              type: string
            event_type:
              type: string
            content_length:
              type: integer
            timestamp:
              type: string
    responses:
      200:
        description: Event recorded
      400:
        description: Bad request
    """
    return event()


@clipboard_bp.route("/summary", methods=["GET"])
@jwt_required
def summary_route():
    """
    Return clipboard event summary for an exam and student.
    ---
    tags:
      - Clipboard
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
      403:
        description: Forbidden
    """
    return summary()


@clipboard_bp.route("/risk-data", methods=["GET"])
@jwt_required
def risk_data_route():
    """
    Return clipboard risk metrics for aggregation.
    ---
    tags:
      - Clipboard
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


@clipboard_bp.route("/health", methods=["GET"])
def health_route():
    """
    Clipboard module health check.
    ---
    tags:
      - Clipboard
    security: []
    responses:
      200:
        description: Module health
    """
    return health()
