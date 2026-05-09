from flask import Blueprint

from middleware.jwt_auth import jwt_required, role_required
from modules.tab.controller import event, summary, risk_data, health

tab_bp = Blueprint("tab_bp", __name__)


@tab_bp.route("/event", methods=["POST"])
@jwt_required
@role_required("student")
def event_route():
    """
    Record a tab visibility/change event from the exam client.
    ---
    tags:
      - Tab
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
            timestamp:
              type: string
    responses:
      200:
        description: Event recorded
      400:
        description: Bad request
    """
    return event()


@tab_bp.route("/summary", methods=["GET"])
@jwt_required
def summary_route():
    """
    Return a per-student summary of tab events for an exam.
    ---
    tags:
      - Tab
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


@tab_bp.route("/risk-data", methods=["GET"])
@jwt_required
def risk_data_route():
    """
    Return risk data used by the risk scoring module.
    ---
    tags:
      - Tab
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


@tab_bp.route("/health", methods=["GET"])
def health_route():
    """
    Tab module health check.
    ---
    tags:
      - Tab
    security: []
    responses:
      200:
        description: Module health
    """
    return health()
