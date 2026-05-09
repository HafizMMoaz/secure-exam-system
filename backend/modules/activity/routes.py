from flask import Blueprint

from middleware.jwt_auth import jwt_required, role_required
from modules.activity.controller import heartbeat, event, summary, risk_data, health

activity_bp = Blueprint("activity_bp", __name__)


@activity_bp.route("/heartbeat", methods=["POST"])
@jwt_required
@role_required("student")
def heartbeat_route():
    """
    Record a student heartbeat and detect idle periods.
    ---
    tags:
      - Activity
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
            - timestamp
          properties:
            exam_id:
              type: string
            timestamp:
              type: string
    responses:
      200:
        description: Heartbeat recorded
      400:
        description: Bad request
    """
    return heartbeat()


@activity_bp.route("/event", methods=["POST"])
@jwt_required
@role_required("student")
def event_route():
    """
    Record a generic exam activity event.
    ---
    tags:
      - Activity
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
            details:
              type: object
            timestamp:
              type: string
    responses:
      200:
        description: Event recorded
      400:
        description: Bad request
    """
    return event()


@activity_bp.route("/summary", methods=["GET"])
@jwt_required
def summary_route():
    """
    Return activity summary for an exam and student.
    ---
    tags:
      - Activity
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


@activity_bp.route("/risk-data", methods=["GET"])
@jwt_required
def risk_data_route():
    """
    Return activity risk data for the risk scoring module.
    ---
    tags:
      - Activity
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


@activity_bp.route("/health", methods=["GET"])
def health_route():
    """
    Activity module health check.
    ---
    tags:
      - Activity
    security: []
    responses:
      200:
        description: Module health
    """
    return health()
