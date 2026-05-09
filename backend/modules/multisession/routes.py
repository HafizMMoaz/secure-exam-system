from flask import Blueprint

from middleware.jwt_auth import jwt_required
from modules.multisession.controller import detect, history, risk_data, health

multisession_bp = Blueprint("multisession_bp", __name__)


@multisession_bp.route("/detect", methods=["POST"])
@jwt_required
def detect_route():
    """
    Detect and invalidate conflicting concurrent sessions for the authenticated user.
    ---
    tags:
      - MultiSession
    security:
      - BearerAuth: []
    responses:
      200:
        description: Multi-session detection result
    """
    return detect()


@multisession_bp.route("/history", methods=["GET"])
@jwt_required
def history_route():
    """
    Return multisession detection history for a user.
    ---
    tags:
      - MultiSession
    security:
      - BearerAuth: []
    parameters:
      - in: query
        name: user_id
        type: string
        required: false
    responses:
      200:
        description: Multisession history returned
      403:
        description: Forbidden
    """
    return history()


@multisession_bp.route("/risk-data", methods=["GET"])
@jwt_required
def risk_data_route():
    """
    Return multisession risk data for aggregation.
    ---
    tags:
      - MultiSession
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


@multisession_bp.route("/health", methods=["GET"])
def health_route():
    """
    MultiSession module health check.
    ---
    tags:
      - MultiSession
    security: []
    responses:
      200:
        description: Module health
    """
    return health()
