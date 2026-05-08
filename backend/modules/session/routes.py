from flask import Blueprint

from middleware.jwt_auth import jwt_required, role_required
from modules.session.controller import create, invalidate, validate, list_all, health

session_bp = Blueprint("session_bp", __name__)


@session_bp.route("/create", methods=["POST"])
@jwt_required
def create_route():
    """
    Create a server-side session for the authenticated user.
    ---
    tags:
      - Session
    security:
      - BearerAuth: []
    responses:
      200:
        description: Session created successfully
      401:
        description: Invalid or missing JWT
    """
    return create()


@session_bp.route("/invalidate", methods=["POST"])
@jwt_required
def invalidate_route():
    """
    Invalidate the authenticated user's session.
    ---
    tags:
      - Session
    security:
      - BearerAuth: []
    responses:
      200:
        description: Session invalidated
      401:
        description: Invalid or missing JWT
    """
    return invalidate()


@session_bp.route("/validate", methods=["GET"])
@jwt_required
def validate_route():
    """
    Validate the authenticated user's session.
    ---
    tags:
      - Session
    security:
      - BearerAuth: []
    responses:
      200:
        description: Session is valid
      401:
        description: Session invalid or expired
    """
    return validate()


@session_bp.route("/list", methods=["GET"])
@jwt_required
@role_required("teacher")
def list_route():
    """
    List sessions (teacher only).
    ---
    tags:
      - Session
    security:
      - BearerAuth: []
    parameters:
      - in: query
        name: user_id
        type: string
    responses:
      200:
        description: Sessions returned
      401:
        description: Invalid or missing JWT
      403:
        description: Insufficient permissions
    """
    return list_all()


@session_bp.route("/health", methods=["GET"])
def health_route():
    """
    Session module health check.
    ---
    tags:
      - Session
    security: []
    responses:
      200:
        description: Module health
    """
    return health()
